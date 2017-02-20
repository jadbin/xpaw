# coding=utf-8

import os
import pickle
import logging
import asyncio
import zipfile
import threading

from kafka import KafkaProducer
from pymongo import MongoClient
from bson.objectid import ObjectId

from xpaw.config import Config
from xpaw.rpc import RpcClient
from xpaw.unikafka import UnikafkaClient
from xpaw.http import HttpRequest, HttpResponse
from xpaw.downloader import Downloader
from xpaw.loader import TaskLoader

log = logging.getLogger(__name__)


class Fetcher:
    def __init__(self, config):
        self._pid = os.getpid()
        if config is None:
            config = Config()

        self._rpc_loop = asyncio.new_event_loop()
        self._master_rpc_client = RpcClient(config["master_addr"], loop=self._rpc_loop)

        remote_config = self._pull_remote_config()
        config.update(remote_config, priority="default")
        self._config = config

        self._downloader_loop = asyncio.new_event_loop()

        self._producer = RequestProducer.from_config(config)

        self._task_config = TaskConfigManager(os.path.join(config["data_dir"] or ".", "task"),
                                              config["mongo_addr"],
                                              config["mongo_dbname"])
        self._unikafka_client = UnikafkaClient.from_config(config)
        self._downloader = Downloader(loop=self._downloader_loop)

        self._task_progress_recorder = TaskProgressRecorder()
        self._new_task_slot_recorder = NewTaskSlotRecorder()
        self._heartbeat_sender = HeartbeatSender(self.send_heartbeat,
                                                 config.get("heartbeat_interval"),
                                                 (
                                                     self._task_progress_recorder.fetch_data,
                                                     self._new_task_slot_recorder.fetch_data
                                                 ),
                                                 (
                                                     self._handle_new_task,
                                                     self._handle_task_gc
                                                 ),
                                                 loop=self._rpc_loop)

        self._is_running = False

    def _pull_remote_config(self):
        try:
            conf = self._rpc_loop.run_until_complete(self._master_rpc_client.get_config())
        except Exception:
            log.error("Unable to get configuration from master")
            raise
        log.info("Get remote configuration: {0}".format(conf))
        return conf

    def start(self):
        if not self._is_running:
            self._is_running = True
            self._start_downloader_loop()
            self._start_rpc_loop()

    def _start_rpc_loop(self):
        def _start():
            asyncio.set_event_loop(self._rpc_loop)
            try:
                self._rpc_loop.run_forever()
            except Exception:
                log.error("Unexpected error occurred when run loop", exc_info=True)
                raise
            finally:
                log.info("Close RPC loop")
                self._rpc_loop.close()

        asyncio.ensure_future(self._heartbeat_sender.send_heartbeat(), loop=self._rpc_loop)
        _start()

    def _start_downloader_loop(self):
        def _start():
            asyncio.set_event_loop(self._downloader_loop)
            try:
                self._downloader_loop.run_forever()
            except Exception:
                log.error("Unexpected error occurred when run loop", exc_info=True)
                raise
            finally:
                log.info("Close downloader loop")
                self._downloader_loop.close()

        for i in range(self._config["downloader_clients"]):
            asyncio.ensure_future(self._pull_requests(), loop=self._downloader_loop)
        t = threading.Thread(target=_start, daemon=True)
        t.start()

    async def _pull_requests(self):
        while self._is_running:
            task_id, data = None, None
            try:
                task_id, data = await self._unikafka_client.poll()
            except Exception:
                log.warning("Unexpected error occurred when poll request", exc_info=True)
            if task_id and data:
                try:
                    req = pickle.loads(data)
                except Exception:
                    log.warning("Cannot load data: {0}".format(data))
                else:
                    log.debug("The request (url={0}) has been pulled".format(req.url))
                    self._task_progress_recorder.pull_request(task_id)
                    req.meta["_task_id"] = task_id
                    downloadermw = self._task_config.downloadermw(task_id)
                    timeout = self._task_config.downloader_timeout(task_id)
                    result = await downloadermw.download(self._downloader,
                                                         req,
                                                         timeout=timeout)
                    self._handle_result(req, result)
            else:
                # sleep when there is no work
                await asyncio.sleep(3, loop=self._downloader_loop)

    def _handle_result(self, request, result):
        task_id = request.meta["_task_id"]
        if isinstance(result, HttpRequest):
            self._push_request(task_id, result)
        elif isinstance(result, HttpResponse):
            # bind HttpRequest
            result.request = request
            spider = self._task_config.spider(task_id)
            spidermw = self._task_config.spidermw(task_id)
            for res in spider.parse(result, middleware=spidermw):
                if isinstance(res, HttpRequest):
                    self._push_request(task_id, res)
                elif isinstance(res, Exception):
                    log.warning("Unexpected error occurred when parse response", exc_info=res)
        elif isinstance(result, Exception):
            log.warn("Unexpected error occurred when request '{0}'".format(request.url), exc_info=result)

    def _push_request(self, task_id, req):
        self._producer.push_request(task_id, req)
        self._task_progress_recorder.push_request(task_id)

    def _handle_new_task(self, data):
        task_id = data.get("new_task")
        if task_id is not None:
            log.info("Add task: {0}".format(task_id))
            self._new_task_slot_recorder.acquire_slot()
            asyncio.run_coroutine_threadsafe(self._add_task(task_id), loop=self._rpc_loop)

    async def _add_task(self, task_id):
        spider = self._task_config.spider(task_id)
        spidermws = self._task_config.spidermw(task_id)
        for res in spider.start_requests(middleware=spidermws):
            if isinstance(res, HttpRequest):
                self._push_request(task_id, res)
            elif isinstance(res, Exception):
                log.warning("Unexpected error occurred when handle start requests", exc_info=res)
            # take a very short break
            await asyncio.sleep(0.001, loop=self._rpc_loop)
        self._new_task_slot_recorder.release_slot()

    def _handle_task_gc(self, data):
        task_set = data.get("task_gc")
        if task_set is not None:
            log.debug("Task GC, keep the following tasks: {0}".format(task_set))
            self._task_config.gc(task_set)

    async def send_heartbeat(self, data):
        res = {}
        try:
            log.debug("Send heartbeat")
            res = await self._master_rpc_client.handle_heartbeat(self._pid, data)
        except Exception:
            log.warning("Unexpected error occurred when send heartbeat", exc_info=True)
        return res


class TaskConfigManager:
    def __init__(self, task_dir, mongo_addr, mongo_dbname):
        self._task_dir = task_dir
        self._mongo_client = MongoClient(mongo_addr)
        self._task_config_tbl = self._mongo_client[mongo_dbname]["task_config"]
        self._set = set()
        self._task_loaders = {}
        self._lock = threading.Lock()

    def gc(self, task_set):
        with self._lock:
            del_task = []
            for t in self._set:
                if t not in task_set:
                    del_task.append(t)
            for t in del_task:
                self._set.remove(t)
                self._remove_task(t)

    def downloadermw(self, task_id):
        with self._lock:
            if task_id not in self._set:
                self._load_task(task_id)
                self._set.add(task_id)
            return self._task_loaders[task_id].downloadermw

    def spider(self, task_id):
        with self._lock:
            if task_id not in self._set:
                self._load_task(task_id)
                self._set.add(task_id)
            return self._task_loaders[task_id].spider

    def spidermw(self, task_id):
        with self._lock:
            if task_id not in self._set:
                self._load_task(task_id)
                self._set.add(task_id)
            return self._task_loaders[task_id].spidermw

    def downloader_timeout(self, task_id):
        with self._lock:
            if task_id not in self._set:
                self._load_task(task_id)
                self._set.add(task_id)
            return self._task_loaders[task_id].config["downloader_timeout"]

    def _load_task(self, task_id):
        code_dir = os.path.join(self._task_dir, task_id)
        self._unzip_task(task_id, code_dir)
        t = TaskLoader(code_dir)
        t.config.set("task_id", task_id, "project")
        self._task_loaders[task_id] = t

    def _remove_task(self, task_id):
        del self._task_loaders[task_id]

    def _unzip_task(self, task_id, code_dir):
        if not os.path.exists(code_dir):
            log.debug("Unzip the code of the task '{0}' at '{1}'".format(task_id, code_dir))
            os.makedirs(code_dir, mode=0o775)
            obj = self._task_config_tbl.find_one({"_id": ObjectId(task_id)})
            zipb = obj["zipfile"]
            zipf = os.path.join(code_dir, "{0}.zip".format(task_id))
            with open(zipf, "wb") as f:
                f.write(zipb)
            with zipfile.ZipFile(zipf, "r") as fz:
                for file in fz.namelist():
                    fz.extract(file, code_dir)


class RequestProducer:
    def __init__(self, kafka_addr):
        self._producer = KafkaProducer(bootstrap_servers=kafka_addr)

    @classmethod
    def from_config(cls, config):
        return cls(config.get("kafka_addr"))

    def push_request(self, topic, req):
        log.debug("Push request (url={0}) into the topic '{1}'".format(req.url, topic))
        try:
            r = pickle.dumps(req)
            self._producer.send(topic, r)
        except Exception:
            log.warning("Unexpected error occurred when push request", exc_info=True)


class HeartbeatSender:
    def __init__(self, send_heartbeat, heartbeat_interval,
                 request_handlers, response_handlers,
                 loop=None):
        self._heartbeat_interval = heartbeat_interval
        self._request_handlers = request_handlers or ()
        self._response_handlers = response_handlers or ()
        self._loop = loop or asyncio.get_event_loop()
        self._send_heartbeat = send_heartbeat

    async def send_heartbeat(self):
        log.info("Start to send heartbeats")
        while True:
            data = {}
            for method in self._request_handlers:
                r = method()
                if r is not None:
                    data.setdefault(r[0], r[1])
            res = await self._send_heartbeat(data)
            for method in self._response_handlers:
                method(res)
            await asyncio.sleep(self._heartbeat_interval, loop=self._loop)


class TaskProgressRecorder:
    def __init__(self):
        self._tasks = {}
        self._lock = threading.Lock()

    def pull_request(self, task_id):
        with self._lock:
            if task_id not in self._tasks:
                self._tasks[task_id] = {"completed": 0, "total": 0}
            t = self._tasks[task_id]
            t["completed"] += 1

    def push_request(self, task_id):
        with self._lock:
            if task_id not in self._tasks:
                self._tasks[task_id] = {"completed": 0, "total": 0}
            t = self._tasks[task_id]
            t["total"] += 1

    def fetch_data(self):
        data = []
        with self._lock:
            for task_id in self._tasks.keys():
                t = self._tasks[task_id]
                data.append(dict(task_id=task_id, **t))
            self._tasks = {}
        return "task_progress", data


class NewTaskSlotRecorder:
    def __init__(self):
        self._has_slot = True
        self._lock = threading.Lock()

    def acquire_slot(self):
        with self._lock:
            self._has_slot = False

    def release_slot(self):
        with self._lock:
            self._has_slot = True

    def fetch_data(self):
        with self._lock:
            if self._has_slot:
                return "new_task_slot", True
