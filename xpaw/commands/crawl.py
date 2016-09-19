# coding=utf-8

import os
import sys
import time
import pickle
import asyncio
import logging
import threading
import logging.config
from collections import deque

import yaml
from bson import ObjectId

from xpaw import cli
from xpaw.errors import UsageError
from xpaw.downloader import Downloader, DownloaderMiddlewareManager
from xpaw.spider import Spider, SpiderMiddlewareManager
from xpaw.http import HttpRequest, HttpResponse

log = logging.getLogger(__name__)


class Command:
    @property
    def description(self):
        return "Start to crawl web pages."

    def add_arguments(self, parser):
        parser.add_argument("-p", "--project", dest="project", metavar="DIR",
                            help="the directory of a task project")
        parser.add_argument("-l", "--logger", dest="logger", metavar="FILE",
                            help="the configuration file of the logger")

    def run(self, args):
        if not args.project:
            project_dir = os.getcwd()
            if not os.path.isfile(os.path.join(project_dir, "config.yaml")):
                raise UsageError("Connot find 'config.yaml' in current working directory, please assign the task project directory")
        else:
            project_dir = os.path.abspath(args.project)
        if args.logger:
            logging.config.dictConfig(self._load_config(args.logger))
        else:
            logging.config.dictConfig(cli.logger)
        cluster = Cluster(project_dir)
        cluster.start()

    @staticmethod
    def _load_config(file):
        with open(file, "r", encoding="utf-8") as f:
            d = yaml.load(f)
            return d


class Cluster:
    def __init__(self, project_dir):
        self._queue = deque()
        self._downloader_loop = asyncio.new_event_loop()
        self._task_loop = asyncio.new_event_loop()
        self._downloader = Downloader(loop=self._downloader_loop)
        with open(os.path.join(project_dir, "config.yaml"), "r", encoding="utf-8") as f:
            task_config = yaml.load(f)
        task_id = "{0}".format(ObjectId())
        log.info("Please remember the task ID: {0}".format(task_id))
        task_config.setdefault("_task_id", task_id)
        task_config.setdefault("_event_loop", self._downloader_loop)
        sys.path.append(project_dir)
        self._downloadermw = DownloaderMiddlewareManager.from_config(task_config)
        self._spider = Spider.from_config(task_config)
        self._spidermw = SpiderMiddlewareManager.from_config(task_config)
        sys.path.remove(project_dir)
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
        try:
            for res in self._spider.start_requests(middleware=self._spidermw):
                if isinstance(res, HttpRequest):
                    self._push_request(res)
        except Exception:
            log.warning("Unexpected error occurred when handle start requests", exc_info=True)

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

        asyncio.ensure_future(self._pull_requests(), loop=self._downloader_loop)
        t = threading.Thread(target=_start)
        t.start()

    async def _pull_requests(self):
        log.info("Start to pull requests")
        last_time = time.time()
        while self._is_running:
            if len(self._queue) > 0:
                data = self._queue.popleft()
                req = pickle.loads(data)
                log.debug("The request (url={0}) has been pulled".format(req.url))
                await self._downloader.add_task(req, self._handle_result, middleware=self._downloadermw)
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
            for res in self._spider.parse(result, middleware=self._spidermw):
                if isinstance(res, HttpRequest):
                    r = pickle.dumps(res)
                    self._queue.append(r)
        else:
            log.debug("Got {0} when request '{1}': {2}".format(type(result), request.url, result))
