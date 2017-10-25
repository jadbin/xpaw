# coding=utf-8

import time
import asyncio
import logging
from os.path import join
import sys
import types
from configparser import ConfigParser
from importlib import import_module

from xpaw.downloader import Downloader
from xpaw.http import HttpRequest, HttpResponse
from xpaw.utils import load_object
from xpaw.errors import IgnoreRequest
from xpaw.downloader import DownloaderMiddlewareManager
from xpaw.spider import SpiderMiddlewareManager
from xpaw.config import Config

log = logging.getLogger(__name__)


class LocalCluster:
    def __init__(self, proj_dir=None, config=None):
        self.config = self._load_task_config(proj_dir, config)
        self.downloader_loop = asyncio.new_event_loop()
        self.downloader_loop.set_exception_handler(self._handle_coro_error)
        self.queue = self._new_object_from_cluster(self.config.get("queue_cls"), self)
        self.dupefilter = self._new_object_from_cluster(self.config.get("dupefilter_cls"), self)
        self.downloader = Downloader(timeout=self.config.getfloat("downloader_timeout"),
                                     loop=self.downloader_loop)
        self.spider = load_object(self.config["spider"])(self.config)
        log.debug("Spider: {}".format(".".join((type(self.spider).__module__,
                                                type(self.spider).__name__))))
        self.downloadermw = DownloaderMiddlewareManager.from_config(self.config)
        self.spidermw = SpiderMiddlewareManager.from_config(self.config)
        self._last_request = None
        self._job_futures = None
        self._job_futures_done = set()
        self._start_future = None
        self._supervisor_future = None

    def start(self):
        self.dupefilter.open()
        self.queue.open()
        self.spider.open()
        self.spidermw.open()
        self.downloadermw.open()
        self._start_downloader_loop()

    def _handle_coro_error(self, loop, context):
        log.error("Error occurred while running event loop: {}".format(context["message"]))

    async def _push_start_requests(self):
        try:
            if hasattr(self.spider.start_requests, "cron_job"):
                tick = self.spider.start_requests.cron_tick
            else:
                tick = 0
            while True:
                for res in self.spidermw.start_requests(self.spider):
                    if isinstance(res, HttpRequest):
                        self._push_without_duplicated(res)
                    await asyncio.sleep(0.01, loop=self.downloader_loop)
                if tick <= 0:
                    break
                await asyncio.sleep(tick, loop=self.downloader_loop)
        except Exception:
            log.warning("Error occurred when handle start requests", exc_info=True)

    def _start_downloader_loop(self):
        self._supervisor_future = asyncio.ensure_future(self._supervisor(), loop=self.downloader_loop)
        self._start_future = asyncio.ensure_future(self._push_start_requests(), loop=self.downloader_loop)
        downloader_clients = self.config.getint("downloader_clients")
        log.debug("Downloader clients: {}".format(downloader_clients))
        self._job_futures = []
        for i in range(downloader_clients):
            f = asyncio.ensure_future(self._pull_requests(i), loop=self.downloader_loop)
            self._job_futures.append(f)

        asyncio.set_event_loop(self.downloader_loop)
        try:
            log.info("Start event loop")
            self.downloader_loop.run_forever()
        except Exception:
            log.error("Fatal error occurred while running event loop", exc_info=True)
        finally:
            log.info("Close event loop")
            self.downloader_loop.close()

    async def _supervisor(self):
        timeout = self.config.getfloat("downloader_timeout")
        task_finished_delay = 2 * timeout
        self._last_request = time.time()
        while True:
            await asyncio.sleep(5, loop=self.downloader_loop)
            if self._start_future.done() and time.time() - self._last_request > task_finished_delay:
                break
            for i in range(len(self._job_futures)):
                f = self._job_futures[i]
                if f.done():
                    if i not in self._job_futures_done:
                        self._job_futures_done.add(i)
                        log.error("Coro[{}] is shut down".format(i))
        asyncio.ensure_future(self.shutdown())

    async def shutdown(self):
        if self._job_futures:
            for f in self._job_futures:
                f.cancel()
        if self._start_future:
            self._start_future.cancel()
        if self._supervisor_future:
            self._supervisor_future.cancel()
        try:
            self.downloadermw.close()
        except Exception:
            log.warning("Error occurred when close downloader middlewares", exc_info=True)
        try:
            self.spidermw.close()
        except Exception:
            log.warning("Error occurred when close spider middlewares", exc_info=True)
        try:
            self.spider.close()
        except Exception:
            log.warning("Error occurred when close spider", exc_info=True)
        try:
            self.queue.close()
        except Exception:
            log.warning("Error occurred when close queue", exc_info=True)
        try:
            self.dupefilter.close()
        except Exception:
            log.warning("Error occurred when close dupefilter", exc_info=True)
        log.info("Event loop will be stopped after 3 seconds")
        await asyncio.sleep(3, loop=self.downloader_loop)
        self.downloader_loop.stop()

    async def _pull_requests(self, coro_id):
        while True:
            req = self.queue.pop()
            if req:
                self._last_request = time.time()
                log.debug("The request (url={}) has been pulled by coro[{}]".format(req.url, coro_id))
                try:
                    result = await self.downloadermw.download(self.downloader, req)
                    self._handle_result(req, result)
                except Exception as e:
                    if not isinstance(e, IgnoreRequest):
                        log.warning("Unexpected error occurred while processing request '{}'".format(req.url),
                                    exc_info=True)
                    try:
                        self.spidermw.handle_error(self.spider, req, e)
                    except Exception:
                        log.warning("Unexpected error occurred in error callback", exc_info=True)
            else:
                await asyncio.sleep(3, loop=self.downloader_loop)

    def _handle_result(self, request, result):
        if isinstance(result, HttpRequest):
            self._push_without_duplicated(result)
        elif isinstance(result, HttpResponse):
            # bind HttpRequest
            result.request = request
            try:
                for res in self.spidermw.parse(self.spider, result):
                    if isinstance(res, HttpRequest):
                        self._push_without_duplicated(res)
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

    def _push_without_duplicated(self, request):
        if not self.dupefilter.is_duplicated(request):
            self.queue.push(request)

    def _load_task_config(self, proj_dir=None, base_config=None):
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
