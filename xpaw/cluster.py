# coding=utf-8

import time
import asyncio
import logging

from xpaw.downloader import Downloader
from xpaw.http import HttpRequest, HttpResponse
from xpaw.loader import TaskLoader
from xpaw.utils import load_object
from xpaw.errors import IgnoreRequest
from xpaw.config import Config

log = logging.getLogger(__name__)


class LocalCluster:
    def __init__(self, proj_dir=None, config=None):
        self._config = config or Config()
        self._queue = self._new_object_from_config(self._config.get("queue_cls"), config)
        self._dupefilter = self._new_object_from_config(self._config.get("dupefilter_cls"), config)
        self._downloader_loop = asyncio.new_event_loop()
        self._downloader_loop.set_exception_handler(self._handle_coro_error)
        self._downloader = Downloader(timeout=self._config.getfloat("downloader_timeout"),
                                      loop=self._downloader_loop)
        self._task_loader = TaskLoader(proj_dir=proj_dir, base_config=self._config,
                                       downloader_loop=self._downloader_loop)
        self._last_request = None
        self._job_futures = None
        self._job_futures_done = set()
        self._start_future = None
        self._supervisor_future = None

    def start(self):
        self._dupefilter.open()
        self._queue.open()
        self._task_loader.open_spider()
        self._start_downloader_loop()

    def _handle_coro_error(self, loop, context):
        log.error("Error occurred while running event loop: {}".format(context["message"]))

    async def _push_start_requests(self):
        try:
            spider = self._task_loader.spider
            if hasattr(spider.start_requests, "cron_job"):
                tick = spider.start_requests.cron_tick
            else:
                tick = 0
            while True:
                for res in self._task_loader.spidermw.start_requests(self._task_loader.spider):
                    if isinstance(res, HttpRequest):
                        self._push_without_duplicated(res)
                    await asyncio.sleep(0.01, loop=self._downloader_loop)
                if tick <= 0:
                    break
                await asyncio.sleep(tick, loop=self._downloader_loop)
        except Exception:
            log.warning("Error occurred when handle start requests", exc_info=True)

    def _start_downloader_loop(self):
        self._supervisor_future = asyncio.ensure_future(self._supervisor(), loop=self._downloader_loop)
        self._start_future = asyncio.ensure_future(self._push_start_requests(), loop=self._downloader_loop)
        downloader_clients = self._task_loader.config.getint("downloader_clients")
        log.debug("Downloader clients: {}".format(downloader_clients))
        self._job_futures = []
        for i in range(downloader_clients):
            f = asyncio.ensure_future(self._pull_requests(i), loop=self._downloader_loop)
            self._job_futures.append(f)

        asyncio.set_event_loop(self._downloader_loop)
        try:
            log.info("Start event loop")
            self._downloader_loop.run_forever()
        except Exception:
            log.error("Fatal error occurred while running event loop", exc_info=True)
            raise
        finally:
            log.info("Close event loop")
            self._downloader_loop.close()

    async def _supervisor(self):
        timeout = self._task_loader.config.getfloat("downloader_timeout")
        task_finished_delay = 2 * timeout
        self._last_request = time.time()
        while True:
            await asyncio.sleep(5, loop=self._downloader_loop)
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
            self._task_loader.close_spider()
        except Exception:
            log.warning("Error occurred when close spider", exc_info=True)
        try:
            self._queue.close()
        except Exception:
            log.warning("Error occurred when close queue", exc_info=True)
        try:
            self._dupefilter.close()
        except Exception:
            log.warning("Error occurred when close dupefilter", exc_info=True)
        log.info("Event loop will be stopped after 3 seconds")
        await asyncio.sleep(3, loop=self._downloader_loop)
        self._downloader_loop.stop()

    async def _pull_requests(self, coro_id):
        while True:
            req = self._queue.pop()
            if req:
                self._last_request = time.time()
                log.debug("The request (url={}) has been pulled by coro[{}]".format(req.url, coro_id))
                try:
                    result = await self._task_loader.downloadermw.download(self._downloader, req)
                    self._handle_result(req, result)
                except Exception as e:
                    if not isinstance(e, IgnoreRequest):
                        log.warning("Unexpected error occurred while processing request '{}'".format(req.url),
                                    exc_info=True)
                    try:
                        self._task_loader.spidermw.handle_error(self._task_loader.spider, req, e)
                    except Exception:
                        log.warning("Unexpected error occurred in error callback", exc_info=True)
            else:
                await asyncio.sleep(3, loop=self._downloader_loop)

    def _handle_result(self, request, result):
        if isinstance(result, HttpRequest):
            self._push_without_duplicated(result)
        elif isinstance(result, HttpResponse):
            # bind HttpRequest
            result.request = request
            try:
                for res in self._task_loader.spidermw.parse(self._task_loader.spider, result):
                    if isinstance(res, HttpRequest):
                        self._push_without_duplicated(res)
            except Exception:
                log.warning("Unexpected error occurred while processing response of '{}'".format(request.url),
                            exc_info=True)

    @staticmethod
    def _new_object_from_config(cls_path, config):
        obj_cls = load_object(cls_path)
        if hasattr(obj_cls, "from_config"):
            obj = obj_cls.from_config(config)
        else:
            obj = obj_cls()
        return obj

    def _push_without_duplicated(self, request):
        if not self._dupefilter.is_duplicated(request):
            self._queue.push(request)
