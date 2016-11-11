# coding=utf-8

import os
import sys
import pickle
import logging
import asyncio
import zipfile
import threading

import yaml
from pykafka import KafkaClient
from pymongo import MongoClient
from bson.objectid import ObjectId

from xpaw.rpc import RpcClient
from xpaw.unikafka import UnikafkaClient
from xpaw.http import HttpRequest, HttpResponse
from xpaw.downloader import Downloader, DownloaderMiddlewareManager
from xpaw.spider import Spider, SpiderMiddlewareManager

log = logging.getLogger(__name__)


class Fetcher:
    def __init__(self, master_rpc_addr, *, local_config=None):
        self._pid = os.getpid()
        if local_config is None:
            local_config = {}

        self._rpc_loop = asyncio.new_event_loop()
        self._master_rpc_client = RpcClient(master_rpc_addr, loop=self._rpc_loop)

        remote_config = self._pull_remote_config()
        if remote_config:
            for k in remote_config:
                local_config.setdefault(k, remote_config[k])

        self._downloader_loop = asyncio.new_event_loop()

        self._producer = RequestProducer.from_config(local_config)

        local_config["event_loop"] = self._downloader_loop
        local_config["downloader_loop"] = self._downloader_loop
        local_config["unikafka_client_loop"] = self._downloader_loop
        self._task_config = TaskConfig.from_config(local_config)
        self._unikafka_client = UnikafkaClient.from_config(local_config)
        self._downloader = Downloader.from_config(local_config)

        self._task_progress_recorder = TaskProgressRecorder.from_config(local_config)
        self._new_task_slot_recorder = NewTaskSlotRecorder.from_config(local_config)
        local_config["heartbeat_sender_loop"] = self._rpc_loop
        local_config["send_heartbeat"] = self.send_heartbeat
        local_config["heartbeat_request_handlers"] = (self._task_progress_recorder.fetch_data,
                                                      self._new_task_slot_recorder.fetch_data)
        local_config["heartbeat_response_handlers"] = (self._handle_new_task,
                                                       self._handle_task_gc)
        self._heartbeat_sender = HeartbeatSender.from_config(local_config)

        self._is_running = False

    @classmethod
    def from_config(cls, config):
        return cls(config.get("master_rpc_addr"), local_config=config)

    def _pull_remote_config(self):
        conf = self._rpc_loop.run_until_complete(self._master_rpc_client.get_config())
        log.info("Get remote configuration: {0}".format(conf))
        return conf

    def start(self):
        if not self._is_running:
            self._is_running = True
            self._start_rpc_loop()
            self._start_downloader_loop()

    def _start_rpc_loop(self):
        def _start():
            asyncio.set_event_loop(self._rpc_loop)
            try:
                self._rpc_loop.run_forever()
            except Exception:
                log.error("Unexpected error occurred when run loop", exc_info=True)
                raise
            finally:
                self._rpc_loop.close()

        asyncio.ensure_future(self._heartbeat_sender.send_heartbeat(), loop=self._rpc_loop)
        t = threading.Thread(target=_start)
        t.start()

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
        while self._is_running:
            task_id, data = None, None
            try:
                task_id, data = await self._unikafka_client.poll()
            except Exception:
                log.warning("Unexpected error occurred when poll request", exc_info=True)
            if task_id and data:
                req = pickle.loads(data)
                log.debug("The request (url={0}) has been pulled".format(req.url))
                self._task_progress_recorder.pull_request(task_id)
                req.meta["_task_id"] = task_id
                await self._downloader.add_task(req,
                                                self._handle_result,
                                                timeout=self._task_config.downloader_timeout(task_id),
                                                middleware=self._task_config.downloadermw(task_id))
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
            self._producer.gc(task_set)

    async def send_heartbeat(self, data):
        return await self._master_rpc_client.handle_heartbeat(self._pid, data)


class TaskConfig:
    def __init__(self, task_dir, mongo_addr, *, mongo_db="xpaw", event_loop=None):
        self._task_dir = task_dir
        self._mongo_client = MongoClient(mongo_addr)
        self._task_config_tbl = self._mongo_client[mongo_db]["task_config"]
        self._event_loop = event_loop or asyncio.get_event_loop()
        self._set = set()
        self._config = {}
        self._downloadermw, self._spider, self._spidermw = {}, {}, {}
        self._lock = threading.Lock()

    @classmethod
    def from_config(cls, config):
        task_dir = os.path.join(config.get("data_dir") or ".", "task")
        kw = {}
        if "mongo_db" in config:
            kw["mongo_db"] = config["mongo_db"]
        kw["event_loop"] = config.get("event_loop")
        return cls(task_dir, config.get("mongo_addr"), **kw)

    def gc(self, task_set):
        with self._lock:
            del_task = []
            for t in self._set:
                if t not in task_set:
                    del_task.append(t)
            for t in del_task:
                self._set.remove(t)
                self._remove_task_config(t)

    def downloadermw(self, task_id):
        with self._lock:
            if task_id not in self._set:
                self._load_task_config(task_id)
                self._set.add(task_id)
            return self._downloadermw[task_id]

    def spider(self, task_id):
        with self._lock:
            if task_id not in self._set:
                self._load_task_config(task_id)
                self._set.add(task_id)
            return self._spider[task_id]

    def spidermw(self, task_id):
        with self._lock:
            if task_id not in self._set:
                self._load_task_config(task_id)
                self._set.add(task_id)
            return self._spidermw[task_id]

    def downloader_timeout(self, task_id):
        with self._lock:
            if task_id not in self._set:
                self._load_task_config(task_id)
                self._set.add(task_id)
            return self._config[task_id].get("downloader_timeout")

    def _load_task_config(self, task_id):
        code_dir = os.path.join(self._task_dir, task_id)
        self._unzip_task(task_id, code_dir)
        config_yaml = os.path.join(code_dir, "config.yaml")
        with open(config_yaml, "r", encoding="utf-8") as f:
            task_config = yaml.load(f)
            log.debug("Loaded the configuration of the task '{0}': {1}".format(task_id, task_config))
        task_config["_task_id"] = task_id
        task_config["_event_loop"] = self._event_loop
        self._config[task_id] = task_config
        self._load_custom_objects(task_id, task_config, code_dir)

    def _remove_task_config(self, task_id):
        self._remove_custom_objects(task_id)
        del self._config[task_id]

    def _remove_custom_objects(self, task_id):
        del self._downloadermw[task_id]
        del self._spider[task_id]
        del self._spidermw[task_id]

    def _load_custom_objects(self, task_id, task_config, code_dir):
        # add project path
        sys.path.append(code_dir)
        # copy sys.modules
        modules_keys = set(sys.modules.keys())
        self._downloadermw[task_id] = DownloaderMiddlewareManager.from_config(task_config)
        self._spider[task_id] = Spider.from_config(task_config)
        self._spidermw[task_id] = SpiderMiddlewareManager.from_config(task_config)
        # recover sys.modules
        keys = list(sys.modules.keys())
        for k in keys:
            if k not in modules_keys:
                del sys.modules[k]
        # remove project path
        sys.path.remove(code_dir)

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
        self._set = set()
        self._producers = {}
        self._kafka_client = KafkaClient(hosts=kafka_addr)
        self._lock = threading.Lock()

    @classmethod
    def from_config(cls, config):
        return cls(config.get("kafka_addr"))

    def gc(self, task_set):
        with self._lock:
            del_task = []
            for t in self._set:
                if t not in task_set:
                    del_task.append(t)
            for t in del_task:
                self._set.remove(t)
                self._producers[t].stop()
                del self._producers[t]

    def push_request(self, topic, req):
        log.debug("Push request (url={0}) into the topic '{1}'".format(req.url, topic))
        r = pickle.dumps(req)
        with self._lock:
            if topic not in self._set:
                self._set.add(topic)
                self._producers[topic] = self._kafka_client.topics[topic.encode("utf-8")].get_producer()
            self._producers[topic].produce(r)


class HeartbeatSender:
    def __init__(self, send_heartbeat, *, heartbeat_interval=10,
                 request_handlers=None, response_handlers=None,
                 loop=None):
        self._heartbeat_interval = heartbeat_interval
        self._request_handlers = request_handlers or ()
        self._response_handlers = response_handlers or ()
        self._loop = loop or asyncio.get_event_loop()
        self._send_heartbeat = send_heartbeat

    @classmethod
    def from_config(cls, config):
        kw = {}
        if "heartbeat_interval" in config:
            kw["heartbeat_interval"] = config["heartbeat_interval"]
        kw["request_handlers"] = config.get("heartbeat_request_handlers")
        kw["response_handlers"] = config.get("heartbeat_response_handlers")
        kw["loop"] = config.get("heartbeat_sender_loop")
        return cls(config.get("send_heartbeat"), **kw)

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

    @classmethod
    def from_config(cls, config):
        return cls()

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

    @classmethod
    def from_config(cls, config):
        return cls()

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
