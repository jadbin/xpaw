# coding=utf-8

import time
import pickle
import asyncio
import threading
import logging.config
from collections import deque

from xpaw.downloader import Downloader
from xpaw.http import HttpRequest, HttpResponse
from xpaw.loader import TaskLoader

log = logging.getLogger(__name__)


class LocalCluster:
    def __init__(self, proj_dir, config):
        self._config = config
        self._queue = deque()
        self._downloader_loop = asyncio.new_event_loop()
        self._downloader_loop.set_exception_handler(self._handle_coro_error)
        self._downloader = Downloader(loop=self._downloader_loop)
        self._task_loader = TaskLoader(proj_dir, downloader_loop=self._downloader_loop)
        self._is_running = False
        self._last_request = None

    def start(self):
        log.info("Task ID: {}".format(self._task_loader.config.get("task_id")))
        self._is_running = True
        self._start_downloader_loop()

    def _handle_coro_error(self, loop, context):
        log.error("Unexpected error occurred when run the event loop: {}".format(context["message"]))

    async def _push_start_requests(self):
        for res in self._task_loader.spidermw.start_requests(self._task_loader.spider):
            if isinstance(res, HttpRequest):
                self._push_request(res)
            elif isinstance(res, Exception):
                log.warning("Unexpected error occurred when handle start requests", exc_info=True)
            await asyncio.sleep(0.01, loop=self._downloader_loop)

    def _push_request(self, req):
        r = pickle.dumps(req)
        self._queue.append(r)

    def _start_downloader_loop(self):
        def _start():
            asyncio.set_event_loop(self._downloader_loop)
            try:
                self._downloader_loop.run_forever()
            except Exception:
                log.error("Unexpected error occurred when run loop", exc_info=True)
                raise
            finally:
                self._downloader_loop.close()

        asyncio.ensure_future(self._push_start_requests(), loop=self._downloader_loop)
        asyncio.ensure_future(self._supervisor(), loop=self._downloader_loop)
        for i in range(self._config["downloader_clients"]):
            asyncio.ensure_future(self._pull_requests(i), loop=self._downloader_loop)
        t = threading.Thread(target=_start)
        t.start()

    async def _supervisor(self):
        timeout = self._task_loader.config["downloader_timeout"]
        task_finished_delay = 2 * timeout
        self._last_request = time.time()
        while self._is_running:
            await asyncio.sleep(5, loop=self._downloader_loop)
            if time.time() - self._last_request > task_finished_delay:
                self._is_running = False
        log.info("Event loop will be stopped after 5 seconds")
        await asyncio.sleep(5, loop=self._downloader_loop)
        self._downloader_loop.stop()

    async def _pull_requests(self, coro_id):
        timeout = self._task_loader.config["downloader_timeout"]
        while self._is_running:
            if len(self._queue) > 0:
                data = self._queue.popleft()
                req = pickle.loads(data)
                self._last_request = time.time()
                log.debug("The request (url={}) has been pulled by coro[{}]".format(req.url, coro_id))
                try:
                    result = await self._task_loader.downloadermw.download(self._downloader, req,
                                                                           timeout=timeout)
                except Exception:
                    log.warning("Unexpected error occurred when request '{}'".format(req.url), exc_info=True)
                else:
                    self._handle_result(req, result)
            else:
                await asyncio.sleep(3, loop=self._downloader_loop)

    def _handle_result(self, request, result):
        if isinstance(result, HttpRequest):
            r = pickle.dumps(result)
            self._queue.append(r)
        elif isinstance(result, HttpResponse):
            # bind HttpRequest
            result.request = request
            try:
                for res in self._task_loader.spidermw.parse(self._task_loader.spider,
                                                            result):
                    if isinstance(res, HttpRequest):
                        r = pickle.dumps(res)
                        self._queue.append(r)
            except Exception:
                log.warning("Unexpected error occurred when parse response", exc_info=True)
