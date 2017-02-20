# coding=utf-8

import time
import pickle
import asyncio
import threading
import logging.config
from collections import deque

from bson import ObjectId

from xpaw.downloader import Downloader
from xpaw.http import HttpRequest, HttpResponse
from xpaw.loader import TaskLoader

log = logging.getLogger(__name__)


class LocalCluster:
    def __init__(self, proj_dir, config):
        self._config = config
        self._queue = deque()
        self._downloader_loop = asyncio.new_event_loop()
        self._task_loop = asyncio.new_event_loop()
        self._downloader = Downloader(loop=self._downloader_loop)
        self._task_loader = TaskLoader(proj_dir)
        task_id = "{0}".format(ObjectId())
        log.info("Please remember the task ID: {0}".format(task_id))
        self._task_loader.config.set("task_id", task_id, "project")
        self._is_running = False

    def start(self):
        self._is_running = True
        self._start_task_loop()
        self._start_downloader_loop()

    def _start_task_loop(self):
        def _start():
            asyncio.set_event_loop(self._task_loop)
            try:
                self._task_loop.run_forever()
            except Exception:
                log.error("Unexpected error occurred when run loop", exc_info=True)
                raise
            finally:
                self._task_loop.close()

        t = threading.Thread(target=_start)
        t.start()
        self._task_loop.call_soon_threadsafe(self._push_start_requests)

    def _push_start_requests(self):
        for res in self._task_loader.spidermw.start_requests(self._task_loader.spider):
            if isinstance(res, HttpRequest):
                self._push_request(res)
            elif isinstance(res, Exception):
                log.warning("Unexpected error occurred when handle start requests", exc_info=res)

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

        for i in range(self._config["downloader_clients"]):
            asyncio.ensure_future(self._pull_requests(), loop=self._downloader_loop)
        t = threading.Thread(target=_start)
        t.start()

    async def _pull_requests(self):
        last_time = time.time()
        while self._is_running:
            if len(self._queue) > 0:
                data = self._queue.popleft()
                req = pickle.loads(data)
                log.debug("The request (url={0}) has been pulled".format(req.url))
                result = await self._task_loader.downloadermw.download(self._downloader, req,
                                                                       timeout=self._task_loader.config[
                                                                           "downloader_timeout"])
                self._handle_result(req, result)
                last_time = time.time()
            else:
                if time.time() - last_time > 30:
                    self._is_running = False
                    self._task_loop.call_soon_threadsafe(self._task_loop.stop)
                    self._downloader_loop.call_soon_threadsafe(self._downloader_loop.stop)
                else:
                    await asyncio.sleep(3, loop=self._downloader_loop)

    def _handle_result(self, request, result):
        if isinstance(result, HttpRequest):
            r = pickle.dumps(result)
            self._queue.append(r)
        elif isinstance(result, HttpResponse):
            # bind HttpRequest
            result.request = request
            for res in self._task_loader.spidermw.parse(self._task_loader.spider,
                                                        result):
                if isinstance(res, HttpRequest):
                    r = pickle.dumps(res)
                    self._queue.append(r)
                elif isinstance(res, Exception):
                    log.warning("Unexpected error occurred when parse response", exc_info=res)
        elif isinstance(result, Exception):
            log.warn("Unexpected error occurred when request '{0}'".format(request.url), exc_info=result)
