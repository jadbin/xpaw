# coding=utf-8

import asyncio
import logging
from asyncio import CancelledError
import time
import inspect

from .downloader import Downloader
from .http import HttpRequest, HttpResponse
from .errors import IgnoreRequest, IgnoreItem, StopCluster, ClientError, HttpError
from .downloader import DownloaderMiddlewareManager
from .spider import Spider, SpiderMiddlewareManager
from .eventbus import EventBus
from . import events
from .extension import ExtensionManager
from .item import BaseItem
from .pipeline import ItemPipelineManager
from .utils import load_object

log = logging.getLogger(__name__)


class LocalCluster:
    def __init__(self, config):
        self.config = config
        self.event_bus = EventBus()
        self.stats_collector = self._new_object_from_cluster(self.config.get('stats_collector'), self)
        self.queue = self._new_object_from_cluster(self.config.get('queue'), self)
        self.dupe_filter = self._new_object_from_cluster(self.config.get('dupe_filter'), self)
        self.downloader = Downloader(self.config.getint('downloader_clients'))
        self.spider = self._new_object_from_cluster(self.config.get('spider'), self)
        assert isinstance(self.spider, Spider), 'spider must inherit from the Spider class'
        log.info('Spider: %s', str(self.spider))
        self.downloadermw = DownloaderMiddlewareManager.from_cluster(self)
        log.info('Downloader middlewares: %s', self._log_objects(self.downloadermw.components))
        self.spidermw = SpiderMiddlewareManager.from_cluster(self)
        log.info('Spider middlewares: %s', self._log_objects(self.spidermw.components))
        self.item_pipeline = ItemPipelineManager.from_cluster(self)
        log.info('Item pipelines: %s', self._log_objects(self.item_pipeline.components))
        self.extension = ExtensionManager.from_cluster(self)
        log.info('Extensions: %s', self._log_objects(self.extension.components))
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
        await self._run()
        self._run_lock = asyncio.Future()
        await self._run_lock
        self._run_lock = None

    async def _run(self):
        await self.event_bus.send(events.cluster_start)
        self._supervisor_future = asyncio.ensure_future(self._supervisor())
        self._start_future = asyncio.ensure_future(self._generate_start_requests())
        downloader_clients = self.downloader.max_clients
        log.info("The maximum number of simultaneous clients: %s", downloader_clients)
        self._workers = []
        for i in range(downloader_clients):
            f = asyncio.ensure_future(self._download(i))
            self._workers.append(f)
        self._workers_done = set()
        self._req_in_worker = [None] * downloader_clients
        log.info('Cluster is loaded')

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
                    await self.queue.push(r)
            self._req_in_worker = None
        await self.event_bus.send(events.cluster_shutdown)
        # wait cancelled futures
        await asyncio.wait(cancelled_futures)
        log.info('Cluster is unloaded')
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
        if self._start_future.done() and len(self.queue) <= 0:
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
        try:
            if hasattr(self.spider.start_requests, "cron_job"):
                tick = self.spider.start_requests.cron_tick
            else:
                tick = 0
            while True:
                t = time.time()
                res = await self.spidermw.start_requests(self.spider)
                for r in res:
                    if isinstance(r, HttpRequest):
                        await self.schedule(r)
                if tick <= 0:
                    break
                t = time.time() - t
                if t < tick:
                    await asyncio.sleep(tick - t)
        except CancelledError:
            raise
        except Exception:
            log.warning("Failed to generate start requests", exc_info=True)

    async def _download(self, coro_id):
        while True:
            req = await self.queue.pop()
            log.debug("%s -> worker[%s]", req, coro_id)
            self._req_in_worker[coro_id] = req
            try:
                resp = await self.downloadermw.fetch(self.downloader, req)
            except CancelledError:
                raise
            except Exception as e:
                if not isinstance(e, (IgnoreRequest, ClientError, HttpError)):
                    log.warning("Failed to request %s", req, exc_info=True)
                if isinstance(e, IgnoreRequest):
                    await self.event_bus.send(events.request_ignored, request=req, error=e)
                elif isinstance(e, (ClientError, HttpError)):
                    log.debug('Failed to make %s: %s', req, e)
                else:
                    log.warning("Failed to make %s", req, exc_info=True)
                await self.spider.request_error(req, e)
            else:
                await self._handle_response(resp)
            self._req_in_worker[coro_id] = None
            # check if it's all done
            if self._all_done():
                self.stop()

    async def _handle_response(self, resp):
        if isinstance(resp, HttpRequest):
            await self.schedule(resp)
        elif isinstance(resp, HttpResponse):
            await self.event_bus.send(events.response_received, response=resp)
            try:
                result = await self.spidermw.parse(self.spider, resp)
            except CancelledError:
                raise
            except Exception as e:
                if isinstance(e, StopCluster):
                    log.info('Request to stop cluster: %s', e)
                    self.stop()
                elif isinstance(e, IgnoreRequest):
                    await self.event_bus.send(events.request_ignored, request=resp.request, error=e)
                else:
                    log.warning("Failed to parse %s", resp, exc_info=True)
            else:
                for r in result:
                    await self._handle_parsing_result(r)

    async def _handle_parsing_result(self, result):
        if isinstance(result, HttpRequest):
            await self.schedule(result)
        elif isinstance(result, (BaseItem, dict)):
            try:
                await self.item_pipeline.handle_item(result)
            except CancelledError:
                raise
            except Exception as e:
                if isinstance(e, IgnoreItem):
                    await self.event_bus.send(events.item_ignored, item=result, error=e)
                else:
                    log.warning("Failed to handle %s", result, exc_info=True)
            else:
                await self.event_bus.send(events.item_scraped, item=result)

    @staticmethod
    def _new_object_from_cluster(cls_path, cluster):
        obj_cls = load_object(cls_path)
        if hasattr(obj_cls, "from_cluster"):
            obj = obj_cls.from_cluster(cluster)
        else:
            obj = obj_cls()
        return obj

    async def schedule(self, request):
        res = self.dupe_filter.is_duplicated(request)
        if inspect.iscoroutine(res):
            res = await res
        if not res:
            await self.event_bus.send(events.request_scheduled, request=request)
            await self.queue.push(request)

    @staticmethod
    def _log_objects(objects):
        if objects:
            return ''.join(['\n\t({}/{}) {}'.format(i + 1, len(objects), o) for i, o in enumerate(objects)])
        return ''
