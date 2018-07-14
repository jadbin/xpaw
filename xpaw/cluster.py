# coding=utf-8

import asyncio
import logging
import signal
from asyncio import CancelledError
import time
import inspect

from .downloader import Downloader
from .http import HttpRequest, HttpResponse
from .errors import IgnoreRequest, IgnoreItem
from .downloader import DownloaderMiddlewareManager
from .spider import Spider, SpiderMiddlewareManager
from .eventbus import EventBus
from . import events
from .extension import ExtensionManager
from .item import BaseItem
from .pipeline import ItemPipelineManager
from . import utils

log = logging.getLogger(__name__)


class LocalCluster:
    def __init__(self, config):
        self.config = config
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        self.event_bus = EventBus()
        self.stats_collector = self._new_object_from_cluster(self.config.get('stats_collector'), self)
        self.queue = self._new_object_from_cluster(self.config.get('queue'), self)
        self.dupe_filter = self._new_object_from_cluster(self.config.get('dupe_filter'), self)
        self.downloader = Downloader(timeout=self.config.getfloat('downloader_timeout'),
                                     verify_ssl=self.config.getbool('verify_ssl'),
                                     loop=self.loop)
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
        self._job_futures = None
        self._job_futures_done = None
        self._req_in_job = None
        self._start_future = None
        self._supervisor_future = None
        self._is_running = False

    def start(self):
        if self._is_running:
            return
        self.loop.run_until_complete(self.event_bus.send(events.cluster_start))
        self._supervisor_future = asyncio.ensure_future(self._supervisor(), loop=self.loop)
        self._start_future = asyncio.ensure_future(self._push_start_requests(), loop=self.loop)
        downloader_clients = self.config.getint("downloader_clients")
        log.info("Downloader clients: %s", downloader_clients)
        self._job_futures = []
        for i in range(downloader_clients):
            f = asyncio.ensure_future(self._pull_requests(i), loop=self.loop)
            self._job_futures.append(f)
        self._job_futures_done = set()
        self._req_in_job = [None] * downloader_clients
        self.loop.add_signal_handler(signal.SIGINT, lambda sig=signal.SIGINT: self.shutdown(sig=sig))
        self.loop.add_signal_handler(signal.SIGTERM, lambda sig=signal.SIGTERM: self.shutdown(sig=sig))
        self._is_running = True
        log.info("Cluster is running")
        try:
            self.loop.run_forever()
        except Exception as e:
            log.error("Fatal error occurred while cluster is running: %s", e)
            raise
        finally:
            log.info("Cluster is stopped")

    def shutdown(self, sig=None):
        if sig is not None:
            log.info('Received shutdown signal: %s', sig)
        if not self._is_running:
            return
        self._is_running = False
        asyncio.ensure_future(self._shutdown(), loop=self.loop)

    async def _shutdown(self):
        log.info("Shutdown now")
        cancelled_futures = []
        if self._job_futures:
            for f in self._job_futures:
                f.cancel()
                cancelled_futures.append(f)
            self._job_futures = None
            self._job_futures_done = None
        if self._start_future:
            self._start_future.cancel()
            cancelled_futures.append(self._start_future)
            self._start_future = None
        if self._supervisor_future:
            self._supervisor_future.cancel()
            cancelled_futures.append(self._supervisor_future)
            self._supervisor_future = None
        # put back the unfinished requests
        if self._req_in_job:
            for r in self._req_in_job:
                if r:
                    await self.queue.push(r)
            self._req_in_job = None
        await self.event_bus.send(events.cluster_shutdown)
        # wait cancelled futures
        await asyncio.wait(cancelled_futures, loop=self.loop)
        self.loop.stop()

    async def _supervisor(self):
        timeout = self.config.getfloat("downloader_timeout")
        while True:
            await asyncio.sleep(timeout, loop=self.loop)
            for i in range(len(self._job_futures)):
                f = self._job_futures[i]
                if f.done():
                    if i not in self._job_futures_done:
                        self._job_futures_done.add(i)
                        reason = "cancelled" if f.cancelled() else str(f.exception())
                        log.error("Worker[%s] is shutdown: %s", i, reason)
                        self._req_in_job[i] = None
            if self._all_done():
                break
        self.shutdown()

    def _all_done(self):
        if self._start_future.done() and len(self.queue) <= 0:
            no_active = True
            for i in range(len(self._job_futures)):
                if self._req_in_job[i]:
                    no_active = False
                    break
            return no_active
        elif len(self._job_futures_done) == len(self._job_futures):
            log.error('No alive worker')
            return True
        return False

    async def _push_start_requests(self):
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
                        await self._push_without_duplication(r)
                if tick <= 0:
                    break
                t = time.time() - t
                if t < tick:
                    await asyncio.sleep(tick - t, loop=self.loop)
        except CancelledError:
            raise
        except Exception as e:
            log.warning("Failed to generate start requests: %s", e)

    async def _pull_requests(self, coro_id):
        while True:
            req = await self.queue.pop()
            log.debug("The request %s has been pulled by worker[%s]", req, coro_id)
            self._req_in_job[coro_id] = req
            try:
                resp = await self.downloadermw.download(self.downloader, req)
            except CancelledError:
                raise
            except Exception as e:
                if not isinstance(e, IgnoreRequest):
                    log.warning("Failed to make the request %s: %s", req, e)
                await self.spider.request_error(req, e)
            else:
                await self._handle_response(req, resp)
            self._req_in_job[coro_id] = None
            # check if it's all done
            if self._all_done():
                self.shutdown()

    async def _handle_response(self, req, resp):
        if isinstance(resp, HttpRequest):
            await self._push_without_duplication(resp)
        elif isinstance(resp, HttpResponse):
            await self.event_bus.send(events.response_received, response=resp)
            try:
                result = await self.spidermw.parse(self.spider, resp)
                for r in result:
                    await self._handle_result(r)
            except CancelledError:
                raise
            except Exception as e:
                log.warning("Failed to parse the response %s: %s", req, e)

    async def _handle_result(self, result):
        if isinstance(result, HttpRequest):
            await self._push_without_duplication(result)
        elif isinstance(result, (BaseItem, dict)):
            try:
                await self.item_pipeline.handle_item(result)
            except CancelledError:
                raise
            except Exception as e:
                if isinstance(e, IgnoreItem):
                    await self.event_bus.send(events.item_ignored, item=result)
                else:
                    log.warning("Failed to handle item: %s", e)
            else:
                await self.event_bus.send(events.item_scraped, item=result)

    @staticmethod
    def _new_object_from_cluster(cls_path, cluster):
        obj_cls = utils.load_object(cls_path)
        if hasattr(obj_cls, "from_cluster"):
            obj = obj_cls.from_cluster(cluster)
        else:
            obj = obj_cls()
        return obj

    async def _push_without_duplication(self, request):
        res = self.dupe_filter.is_duplicated(request)
        if inspect.iscoroutine(res):
            res = await res
        if not res:
            await self.event_bus.send(events.request_scheduled, request=request)
            await self.queue.push(request)

    @staticmethod
    def _log_objects(objects):
        if objects:
            return ''.join(['\n\t' + str(i) for i in objects])
        return ''
