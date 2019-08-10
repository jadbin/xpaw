# coding=utf-8

import asyncio
import logging
from asyncio import CancelledError
import time
import inspect

from .http import HttpRequest, HttpResponse
from .errors import IgnoreRequest, IgnoreItem, StopCrawler, ClientError, HttpError
from .spider import Spider
from .eventbus import EventBus
from . import events
from .extension import ExtensionManager
from .item import BaseItem
from .utils import load_object, iterable_to_list, isiterable

log = logging.getLogger(__name__)


class Crawler:
    def __init__(self, config):
        self.config = config
        self.event_bus = EventBus()
        self.stats_collector = self._instance_from_crawler(self.config.get('stats_collector'))
        self.queue = self._instance_from_crawler(self.config.get('queue'))
        self.dupe_filter = self._instance_from_crawler(self.config.get('dupe_filter'))
        self.downloader = self._instance_from_crawler(self.config.get('downloader'))
        self.spider = self._instance_from_crawler(self.config.get('spider'))
        assert isinstance(self.spider, Spider), 'spider must inherit from the Spider class'
        log.info('Spider: %s', str(self.spider))
        self.extension = ExtensionManager.from_crawler(self)
        log.info('Extensions: %s', self._log_objects(self.extension.components))

    async def start_requests(self):
        try:
            res = await self._start_requests()
        except CancelledError:
            raise
        except Exception:
            log.warning("Failed to get start requests", exc_info=True)
        else:
            return [r for r in res if isinstance(r, HttpRequest)]

    async def _start_requests(self):
        res = self.spider.start_requests()
        if inspect.iscoroutine(res):
            res = await res
        assert res is None or isiterable(res), \
            "Start requests must be None or an iterable object, got {}".format(type(res).__name__)
        result = await iterable_to_list(res)
        if result:
            res = await self.extension.handle_start_requests(result)
            result = await iterable_to_list(res)
        return result

    async def schedule(self, request):
        try:
            res = self.dupe_filter.is_duplicated(request)
            if inspect.iscoroutine(res):
                res = await res
            if not res:
                await self.event_bus.send(events.request_scheduled, request=request)
                await self.queue.push(request)
        except Exception:
            log.warning('Failed to schedule %s', request, exc_info=True)

    async def next_request(self):
        req = await self.queue.pop()
        return req

    async def fetch(self, req):

        try:
            resp = await self._fetch(req)
        except CancelledError:
            raise
        except Exception as e:
            if isinstance(e, IgnoreRequest):
                await self.event_bus.send(events.request_ignored, request=req, error=e)
            elif isinstance(e, (ClientError, HttpError)):
                log.info('Failed to make %s: %s', req, e)
            else:
                log.warning("Failed to request %s", req, exc_info=True)
            await self.spider.request_error(req, e)
        else:
            await self._handle_response(resp)

    async def _fetch(self, req):
        try:
            res = await self.extension.handle_request(req)
            if isinstance(res, HttpRequest):
                return res
            if res is None:
                res = await self.downloader.fetch(req)
        except CancelledError:
            raise
        except Exception as e:
            res = await self.extension.handle_error(req, e)
            if isinstance(res, Exception):
                raise res
        if isinstance(res, HttpResponse):
            _res = await self.extension.handle_response(req, res)
            if _res:
                res = _res
            # bind request
            res.request = req
        return res

    async def _handle_response(self, resp):
        if isinstance(resp, HttpRequest):
            await self.schedule(resp)
        elif isinstance(resp, HttpResponse):
            await self.event_bus.send(events.response_received, response=resp)
            try:
                result = await self._parse(resp)
            except CancelledError:
                raise
            except Exception as e:
                if isinstance(e, StopCrawler):
                    log.info('Request to stop crawler: %s', e)
                    raise
                elif isinstance(e, IgnoreRequest):
                    await self.event_bus.send(events.request_ignored, request=resp.request, error=e)
                else:
                    log.warning("Failed to parse %s", resp, exc_info=True)
            else:
                for r in result:
                    await self._handle_parsing_result(r)

    async def _parse(self, response):
        request = response.request
        try:
            try:
                await self.extension.handle_spider_input(response)
            except CancelledError:
                raise
            except Exception as e:
                await self.spider.request_error(request, e)
                raise e
            res = await self.spider.request_success(response)
            assert res is None or isiterable(res), \
                "Parsing result must be None or an iterable object, got {}".format(type(res).__name__)
            result = await iterable_to_list(res)
        except CancelledError:
            raise
        except Exception as e:
            res = await self.extension.handle_spider_error(response, e)
            if isinstance(res, Exception):
                raise res
            result = await iterable_to_list(res)
        if result:
            res = await self.extension.handle_spider_output(response, result)
            result = await iterable_to_list(res)
        return result

    async def _handle_parsing_result(self, result):
        if isinstance(result, HttpRequest):
            await self.schedule(result)
        elif isinstance(result, (BaseItem, dict)):
            try:
                await self.extension.handle_item(result)
            except CancelledError:
                raise
            except Exception as e:
                if isinstance(e, IgnoreItem):
                    await self.event_bus.send(events.item_ignored, item=result, error=e)
                else:
                    log.warning("Failed to handle %s", result, exc_info=True)
            else:
                await self.event_bus.send(events.item_scraped, item=result)

    def _instance_from_crawler(self, cls_path):
        obj_cls = load_object(cls_path)
        if inspect.isclass(obj_cls):
            if hasattr(obj_cls, "from_crawler"):
                obj = obj_cls.from_crawler(self)
            else:
                obj = obj_cls()
        else:
            obj = obj_cls
        return obj

    @staticmethod
    def _log_objects(objects):
        if objects:
            return ''.join(['\n\t({}/{}) {}'.format(i + 1, len(objects), o) for i, o in enumerate(objects)])
        return ''


class CrawlerRunner:
    def __init__(self, crawler):
        self.crawler = crawler

        self._workers = None
        self._workers_done = None
        self._req_in_worker = None
        self._start_future = None
        self._supervisor_future = None
        self._is_running = False
        self._run_lock = None

    async def run(self):
        if self._is_running:
            return
        self._is_running = True
        await self._init()
        self._run_lock = asyncio.Future()
        await self._run_lock
        self._run_lock = None

    async def _init(self):
        await self.crawler.event_bus.send(events.crawler_start)
        self._supervisor_future = asyncio.ensure_future(self._supervisor())
        self._start_future = asyncio.ensure_future(self._generate_start_requests())
        downloader_clients = self.crawler.downloader.max_clients
        log.info("The maximum number of simultaneous clients: %s", downloader_clients)
        self._workers = []
        for i in range(downloader_clients):
            f = asyncio.ensure_future(self._download(i))
            self._workers.append(f)
        self._workers_done = set()
        self._req_in_worker = [None] * downloader_clients
        log.info('Crawler is initialized')

    def stop(self):
        if not self._is_running:
            return
        self._is_running = False
        asyncio.ensure_future(self._shutdown())

    async def _shutdown(self):
        log.info("Shutdown now")
        cancelled_futures = []
        if self._workers:
            for f in self._workers:
                f.cancel()
                cancelled_futures.append(f)
            self._workers = None
            self._workers_done = None
        if self._start_future:
            self._start_future.cancel()
            cancelled_futures.append(self._start_future)
            self._start_future = None
        if self._supervisor_future:
            self._supervisor_future.cancel()
            cancelled_futures.append(self._supervisor_future)
            self._supervisor_future = None
        # put back the unfinished requests
        if self._req_in_worker:
            for r in self._req_in_worker:
                if r:
                    await self.crawler.schedule(r)
            self._req_in_worker = None
        await self.crawler.event_bus.send(events.crawler_shutdown)
        # wait cancelled futures
        await asyncio.wait(cancelled_futures)
        log.info('Crawler is stopped')
        if self._run_lock:
            self._run_lock.set_result(True)

    async def _supervisor(self):
        while True:
            await asyncio.sleep(5)
            for i in range(len(self._workers)):
                f = self._workers[i]
                if f.done():
                    if i not in self._workers_done:
                        self._workers_done.add(i)
                        reason = "This future is cancelled" if f.cancelled() else str(f.exception())
                        log.error("Worker[%s] is shutdown: %s", i, reason)
                        self._req_in_worker[i] = None
            if self._all_done():
                break
        self.stop()

    def _all_done(self):
        if self._start_future.done() and len(self.crawler.queue) <= 0:
            no_active = True
            for i in range(len(self._workers)):
                if self._req_in_worker[i]:
                    no_active = False
                    break
            return no_active
        elif len(self._workers_done) == len(self._workers):
            log.error('No alive worker')
            return True
        return False

    async def _generate_start_requests(self):
        if hasattr(self.crawler.spider.start_requests, "cron_job"):
            tick = self.crawler.spider.start_requests.cron_tick
        else:
            tick = 0
        while True:
            t = time.time()
            reqs = await self.crawler.start_requests()
            for r in reqs:
                await self.crawler.schedule(r)
            if tick <= 0:
                break
            t = time.time() - t
            if t < tick:
                await asyncio.sleep(tick - t)

    async def _download(self, coro_id):
        while True:
            req = await self.crawler.next_request()
            log.debug("%s -> worker[%s]", req, coro_id)
            self._req_in_worker[coro_id] = req
            try:
                await self.crawler.fetch(req)
            except StopCrawler:
                self.stop()
                continue
            self._req_in_worker[coro_id] = None
            # check if it's all done
            if self._all_done():
                self.stop()
