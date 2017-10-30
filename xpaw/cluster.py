# coding=utf-8

import time
import asyncio
import logging
from os.path import join
import sys
import types
from configparser import ConfigParser
from importlib import import_module
import signal

from xpaw.downloader import Downloader
from xpaw.http import HttpRequest, HttpResponse
from xpaw.utils import load_object, AsyncGenWrapper
from xpaw.errors import IgnoreRequest
from xpaw.downloader import DownloaderMiddlewareManager
from xpaw.spider import SpiderMiddlewareManager
from xpaw.config import Config
from xpaw.eventbus import EventBus
from xpaw import events
from xpaw.extension import ExtensionManager

log = logging.getLogger(__name__)


class LocalCluster:
    def __init__(self, proj_dir=None, config=None):
        self.config = self._load_task_config(proj_dir, config)
        self.loop = asyncio.new_event_loop()
        self.event_bus = EventBus()
        self.stats_center = self._new_object_from_cluster(self.config.get("stats_center_cls"), self)
        self.queue = self._new_object_from_cluster(self.config.get("queue_cls"), self)
        self.dupe_filter = self._new_object_from_cluster(self.config.get("dupe_filter_cls"), self)
        self.downloader = Downloader(self.config.getfloat("downloader_timeout"),
                                     self.config.getbool("downloader_verify_ssl"),
                                     loop=self.loop)
        self.spider = self._new_object_from_cluster(self.config.get("spider"), self)
        log.info("Spider: {}".format(".".join((type(self.spider).__module__,
                                               type(self.spider).__name__))))
        self.downloadermw = DownloaderMiddlewareManager.from_cluster(self)
        self.spidermw = SpiderMiddlewareManager.from_cluster(self)
        self.extensions = ExtensionManager.from_cluster(self)
        self._last_request = None
        self._job_futures = None
        self._job_futures_done = set()
        self._start_future = None
        self._supervisor_future = None
        self._is_running = False

    def start(self):
        asyncio.ensure_future(self.event_bus.send(events.cluster_start), loop=self.loop)
        self._supervisor_future = asyncio.ensure_future(self._supervisor(), loop=self.loop)
        self._start_future = asyncio.ensure_future(self._push_start_requests(), loop=self.loop)
        downloader_clients = self.config.getint("downloader_clients")
        log.info("Downloader clients: {}".format(downloader_clients))
        self._job_futures = []
        for i in range(downloader_clients):
            f = asyncio.ensure_future(self._pull_requests(i), loop=self.loop)
            self._job_futures.append(f)

        self.loop.add_signal_handler(signal.SIGINT, lambda: asyncio.ensure_future(self.shutdown()))
        self.loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.ensure_future(self.shutdown()))
        asyncio.set_event_loop(self.loop)
        self._is_running = True
        log.info("Cluster is running")
        try:
            self.loop.run_forever()
        except Exception:
            log.error("Fatal error occurred while running cluster", exc_info=True)
        finally:
            self.loop.close()
            log.info("Cluster is stopped")

    async def _push_start_requests(self):
        try:
            if hasattr(self.spider.start_requests, "cron_job"):
                tick = self.spider.start_requests.cron_tick
            else:
                tick = 0
            while True:
                res = await self.spidermw.start_requests(self.spider)
                if not hasattr(res, "__aiter__"):
                    res = AsyncGenWrapper(res)
                async for r in res:
                    if isinstance(r, HttpRequest):
                        await self._push_without_duplicated(r)
                    await asyncio.sleep(0.01, loop=self.loop)
                if tick <= 0:
                    break
                await asyncio.sleep(tick, loop=self.loop)
        except Exception:
            log.warning("Error occurred when handle start requests", exc_info=True)

    async def _supervisor(self):
        timeout = self.config.getfloat("downloader_timeout")
        task_finished_delay = 2 * timeout
        self._last_request = time.time()
        while True:
            await asyncio.sleep(5, loop=self.loop)
            if self._start_future.done() and time.time() - self._last_request > task_finished_delay:
                break
            for i in range(len(self._job_futures)):
                f = self._job_futures[i]
                if f.done():
                    if i not in self._job_futures_done:
                        self._job_futures_done.add(i)
                        reason = "cancelled" if f.cancelled() else str(f.exception())
                        log.error("Coro[{}] is shut down: {}".format(i, reason))
        asyncio.ensure_future(self.shutdown())

    async def shutdown(self):
        if not self._is_running:
            return
        self._is_running = False
        log.info("Shutdown now")
        if self._job_futures:
            for f in self._job_futures:
                f.cancel()
        if self._start_future:
            self._start_future.cancel()
        if self._supervisor_future:
            self._supervisor_future.cancel()
        await self.event_bus.send(events.cluster_shutdown)
        await asyncio.sleep(0.001, loop=self.loop)
        self.loop.stop()

    async def _pull_requests(self, coro_id):
        while True:
            req = await self.queue.pop()
            self._last_request = time.time()
            log.debug("The request (url={}) has been pulled by coro[{}]".format(req.url, coro_id))
            try:
                result = await self.downloadermw.download(self.downloader, req)
                await self._handle_result(req, result)
            except Exception as e:
                if not isinstance(e, IgnoreRequest):
                    log.warning("Unexpected error occurred while processing request '{}'".format(req.url),
                                exc_info=True)
                try:
                    await self.spidermw.handle_error(self.spider, req, e)
                except Exception:
                    log.warning("Unexpected error occurred in error callback", exc_info=True)

    async def _handle_result(self, request, result):
        if isinstance(result, HttpRequest):
            await self._push_without_duplicated(result)
        elif isinstance(result, HttpResponse):
            # bind HttpRequest
            result.request = request
            await self.event_bus.send(events.response_received, response=result)
            try:
                res = await self.spidermw.parse(self.spider, result)
                if not hasattr(res, "__aiter__"):
                    res = AsyncGenWrapper(res)
                async for r in res:
                    if isinstance(r, HttpRequest):
                        await self._push_without_duplicated(r)
            except Exception:
                log.warning("Unexpected error occurred while processing response of '{}'".format(request.url),
                            exc_info=True)

    @staticmethod
    def _new_object_from_cluster(cls_path, cluster):
        obj_cls = load_object(cls_path)
        if hasattr(obj_cls, "from_cluster"):
            obj = obj_cls.from_cluster(cluster)
        else:
            obj = obj_cls()
        return obj

    async def _push_without_duplicated(self, request):
        if not await self.dupe_filter.is_duplicated(request):
            await self.event_bus.send(events.request_scheduled, request=request)
            await self.queue.push(request)

    @staticmethod
    def _load_task_config(proj_dir=None, base_config=None):
        if proj_dir is not None and proj_dir not in sys.path:
            # add project path
            sys.path.append(proj_dir)
        task_config = base_config or Config()
        if proj_dir is not None:
            config_parser = ConfigParser()
            config_parser.read(join(proj_dir, "setup.cfg"))
            config_path = config_parser.get("config", "default")
            log.debug('Default project configuration: {}'.format(config_path))
            module = import_module(config_path)
            for key in dir(module):
                if not key.startswith("_"):
                    value = getattr(module, key)
                    if not isinstance(value, (types.FunctionType, types.ModuleType, type)):
                        task_config.set(key.lower(), value, "project")
        return task_config
