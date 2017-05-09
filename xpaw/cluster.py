# coding=utf-8

import time
import asyncio
import logging

from xpaw.downloader import Downloader
from xpaw.http import HttpRequest, HttpResponse
from xpaw.loader import TaskLoader
from xpaw.utils.project import load_object

log = logging.getLogger(__name__)


class LocalCluster:
    def __init__(self, proj_dir, config):
        self._config = config
        self._queue = load_object(self._config.get("queue_cls"))()
        self._downloader_loop = asyncio.new_event_loop()
        self._downloader_loop.set_exception_handler(self._handle_coro_error)
        self._downloader = Downloader(timeout=self._config.getfloat("downloader_timeout"),
                                      loop=self._downloader_loop)
        self._task_loader = TaskLoader(proj_dir, base_config=self._config, downloader_loop=self._downloader_loop)
        self._last_request = None
        self._futures = None

    def start(self):
        self._task_loader.open_spider()
        self._start_downloader_loop()

    def _handle_coro_error(self, loop, context):
        log.error("Error while running event loop: {}".format(context["message"]))

    async def _push_start_requests(self):
        try:
            for res in self._task_loader.spidermw.start_requests(self._task_loader.spider):
                if isinstance(res, HttpRequest):
                    self._queue.push(res)
                await asyncio.sleep(0.01, loop=self._downloader_loop)
        except Exception:
            log.warning("Error while handling start requests", exc_info=True)

    def _start_downloader_loop(self):
        self._futures = []
        f = asyncio.ensure_future(self._push_start_requests(), loop=self._downloader_loop)
        self._futures.append(f)
        asyncio.ensure_future(self._supervisor(), loop=self._downloader_loop)
        for i in range(self._task_loader.config.getint("downloader_clients")):
            f = asyncio.ensure_future(self._pull_requests(i), loop=self._downloader_loop)
            self._futures.append(f)

        asyncio.set_event_loop(self._downloader_loop)
        try:
            log.info("Start event loop")
            self._downloader_loop.run_forever()
        except Exception:
            log.error("Error while running event loop", exc_info=True)
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
            if time.time() - self._last_request > task_finished_delay:
                break
        try:
            self._task_loader.close_spider()
        except Exception:
            log.warning("Error while closing spider", exc_info=True)
        if self._futures:
            for f in self._futures:
                f.cancel()
            self._futures = None
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
                except Exception as e:
                    log.warning("Error while processing request '{}'".format(req.url), exc_info=True)
                    try:
                        self._task_loader.spidermw.handle_error(self._task_loader.spider, req, e)
                    except Exception:
                        log.warn("Another error while handling error", exc_info=True)
                else:
                    self._handle_result(req, result)
            else:
                await asyncio.sleep(3, loop=self._downloader_loop)

    def _handle_result(self, request, result):
        if isinstance(result, HttpRequest):
            self._queue.push(result)
        elif isinstance(result, HttpResponse):
            # bind HttpRequest
            result.request = request
            try:
                for res in self._task_loader.spidermw.parse(self._task_loader.spider, result):
                    if isinstance(res, HttpRequest):
                        self._queue.push(res)
            except Exception:
                log.warning("Error while processing response of '{}'".format(request.url), exc_info=True)
