# coding=utf-8

import time
import logging
import asyncio
from collections import deque

from bson.objectid import ObjectId
from pymongo import MongoClient

from xpaw.rpc import RpcServer
from xpaw.unikafka import Unikafka

log = logging.getLogger(__name__)


class Master(object):
    def __init__(self, config):
        self._config = config

        self._rpc_loop = asyncio.new_event_loop()

        task_progress_handler = TaskProgressHandler(self._config["mongo_addr"],
                                                    self._config["mongo_dbname"],
                                                    self.finish_task,
                                                    self._config["task_finished_delay"])
        task_gc_handler = TaskGcHandler(self.get_running_tasks,
                                        self._config["task_gc_interval"])
        self._heartbeat_handler = HeartbeatHandler((task_progress_handler.recheck,),
                                                   self._config["task_recheck_interval"],
                                                   (
                                                       self._assign_new_task,
                                                       task_progress_handler.handle_data,
                                                       task_gc_handler.handle_data
                                                   ),
                                                   loop=self._rpc_loop)

        self._task_db = TaskDb.from_config(self._config)

        self._unikafka = Unikafka(self._config["unikafka_listen"],
                                  self._config["kafka_addr"],
                                  loop=self._rpc_loop)
        self._rpc_server = self._create_rpc_server(self._rpc_loop)

        self._tasks, self._new_tasks = set(), deque()
        self._is_running = False

    def start(self):
        if not self._is_running:
            self._is_running = True
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

        asyncio.ensure_future(self._heartbeat_handler.recheck(), loop=self._rpc_loop)
        self._unikafka.start()
        self._rpc_server.start()
        _start()

    def _create_rpc_server(self, loop):
        master_listen = self._config["master_listen"]
        log.info("Start RPC server on '{0}'".format(master_listen))
        server = RpcServer(master_listen, loop=loop)
        server.register_function(self.create_task)
        server.register_function(self.start_task)
        server.register_function(self.stop_task)
        server.register_function(self.finish_task)
        server.register_function(self.remove_task)
        server.register_function(self.get_config)
        server.register_function(self.get_task_info)
        server.register_function(self.get_task_progress)
        server.register_function(self.get_running_tasks)
        server.register_function(self.handle_heartbeat)
        return server

    def create_task(self, task_info, task_config_zip):
        task = TaskInfo(**task_info)
        task.status = TaskInfo.CREATED
        if task.create_time is None:
            task.create_time = int(time.time())
        log.info("Create the task '{0}'".format(task_info))
        self._task_db.insert_info(task.id, task.json)
        self._task_db.insert_config(task.id, task_config_zip)
        return task.id

    def start_task(self, task_id):
        log.info("Start the task '{0}'".format(task_id))
        task = TaskInfo(**self._task_db.get_info(task_id))
        if task.status not in self._tasks and task.status != TaskInfo.REMOVED:
            if task.status == TaskInfo.CREATED:
                self._new_tasks.append(task_id)
            self._task_db.update_info(task_id, {"$set": {"status": TaskInfo.RUNNING}})
            if task_id not in self._tasks:
                self._tasks.add(task_id)
                self._update_tasks()

    def stop_task(self, task_id):
        log.info("Stop the task '{0}'".format(task_id))
        if task_id in self._tasks:
            self._task_db.update_info(task_id, {"$set": {"status": TaskInfo.STOPPED}})
            self._tasks.remove(task_id)
            self._update_tasks()

    def finish_task(self, task_id):
        log.info("Finish the task '{0}'".format(task_id))
        if task_id in self._tasks:
            self._task_db.update_info(task_id, {"$set": {"status": TaskInfo.FINISHED,
                                                         "finish_time": int(time.time())}})
            self._tasks.remove(task_id)
            self._update_tasks()

    def remove_task(self, task_id):
        log.info("Remove the task '{0}'".format(task_id))
        task = TaskInfo(**self._task_db.get_info(task_id))
        if task.status in (TaskInfo.CREATED, TaskInfo.STOPPED, TaskInfo.FINISHED):
            self._task_db.update_info(task_id, {"$set": {"status": TaskInfo.REMOVED}})

    def get_config(self, _host):
        log.info("Return the local configuration to '{0}': {1}".format(_host, self._config))
        return self._config

    def get_task_info(self, task_id):
        task_info = self._task_db.get_info(task_id)
        log.debug("Return the information of task '{0}': {1}".format(task_id, task_info))
        return task_info

    def get_task_progress(self, task_id):
        task_progress = self._task_db.get_progress(task_id)
        log.debug("Return the progress of task '{0}': {1}".format(task_id, task_progress))
        return task_progress

    def get_running_tasks(self):
        log.debug("Return the running tasks: {0}".format(self._tasks))
        return self._tasks

    def _update_tasks(self):
        asyncio.run_coroutine_threadsafe(self._unikafka.subscribe([i for i in self._tasks]),
                                         loop=self._rpc_loop)

    def handle_heartbeat(self, _host, pid, data):
        identity = (_host, pid)
        log.debug("Handle heartbeat from {0}".format(identity))
        res = self._heartbeat_handler.handle_heartbeat(identity, data)
        return res

    def _assign_new_task(self, identity, data):
        if len(self._new_tasks) > 0:
            slot = data.get("new_task_slot", False)
            if slot is None:
                slot = True
            if slot:
                new_task = self._new_tasks.popleft()
                return "new_task", new_task


class TaskInfo:
    CREATED = 0
    RUNNING = 1
    STOPPED = 2
    FINISHED = 3
    REMOVED = 4

    def __init__(self, **kw):
        self.id = kw.get("id", "{0}".format(ObjectId()))
        self.create_time = kw.get("create_time")
        self.finish_time = kw.get("finish_time")
        self.status = kw.get("status")
        self.description = kw.get("description")

    @property
    def json(self):
        return {
            "id": self.id,
            "create_time": self.create_time,
            "finish_time": self.finish_time,
            "status": self.status,
            "description": self.description
        }


class TaskDb:
    def __init__(self, mongo_addr, *, mongo_db="xpaw"):
        mongo_client = MongoClient(mongo_addr)
        self._info_tbl = mongo_client[mongo_db]["task_info"]
        self._config_tbl = mongo_client[mongo_db]["task_config"]
        self._progress_tbl = mongo_client[mongo_db]["task_progress"]

    @classmethod
    def from_config(cls, config):
        return cls(config.get("mongo_addr"))

    def insert_info(self, task_id, task_info):
        self._info_tbl.insert_one({"_id": ObjectId(task_id), **task_info})

    def update_info(self, task_id, update):
        self._info_tbl.update_one({"_id": ObjectId(task_id)}, update)

    def insert_config(self, task_id, task_config_zip):
        self._config_tbl.insert_one({"_id": ObjectId(task_id), "zipfile": task_config_zip})

    def get_info(self, task_id):
        task_info = self._info_tbl.find_one({"_id": ObjectId(task_id)})
        if task_info:
            del task_info["_id"]
        return task_info

    def get_progress(self, task_id):
        task_progress = self._progress_tbl.find_one({"_id": ObjectId(task_id)})
        if task_progress:
            del task_progress["_id"]
        return task_progress


class HeartbeatHandler:
    def __init__(self, recheck_handlers, recheck_interval, data_handlers, loop=None):
        self._recheck_interval = recheck_interval
        self._recheck_handlers = recheck_handlers or ()
        self._data_handlers = data_handlers or ()
        self._loop = loop or asyncio.get_event_loop()

    def handle_heartbeat(self, identity, data):
        res = {}
        for method in self._data_handlers:
            r = method(identity, data)
            if r is not None:
                res.setdefault(r[0], r[1])
        return res

    async def recheck(self):
        while True:
            for method in self._recheck_handlers:
                method()
            await asyncio.sleep(self._recheck_interval, loop=self._loop)


class TaskProgressHandler:
    def __init__(self, mongo_addr, mongo_db, finish_task, task_finished_delay):
        mongo_client = MongoClient(mongo_addr)
        self._task_progress_tbl = mongo_client[mongo_db]["task_progress"]
        self._finish_task = finish_task
        self._task_finished_delay = task_finished_delay
        self._last_modified = {}

    def handle_data(self, identity, data):
        progress_list = data.get("task_progress")
        if progress_list:
            log.debug("Handle task progress data: {0}".format(progress_list))
            t = time.time()
            for progress in progress_list:
                completed, total = progress["completed"], progress["total"]
                if completed > 0 or total > 0:
                    task_id = progress["task_id"]
                    self._last_modified[task_id] = t
                    try:
                        self._update_database(task_id, completed, total)
                    except Exception:
                        log.warning("Unexpected error occurred when handling data", exc_info=True)

    def recheck(self):
        t = time.time()
        for task_id in [i for i in self._last_modified.keys()]:
            if t - self._last_modified[task_id] > self._task_finished_delay:
                log.debug("The task '{0}' has not been updated in the last {1} seconds".format(task_id,
                                                                                               self._task_finished_delay))
                del self._last_modified[task_id]
                self._finish_task(task_id)

    def _update_database(self, task_id, completed, total):
        obj_id = ObjectId(task_id)
        json = self._task_progress_tbl.find_one({"_id": obj_id})
        if json is None:
            self._task_progress_tbl.insert_one({"_id": obj_id,
                                                "completed": completed,
                                                "total": total,
                                                "last_modified": time.time()})
        else:
            self._task_progress_tbl.update_one({"_id": obj_id},
                                               {"$inc": {"completed": completed,
                                                         "total": total}})
            self._task_progress_tbl.update_one({"_id": obj_id},
                                               {"$set": {"last_modified": time.time()}})


class TaskGcHandler:
    def __init__(self, get_running_tasks, gc_interval):
        self._get_running_tasks = get_running_tasks
        self._gc_interval = gc_interval
        self._last_gc_time = {}

    def handle_data(self, identity, data):
        t = time.time()
        if identity not in self._last_gc_time:
            self._last_gc_time[identity] = t
        elif t - self._last_gc_time[identity] > self._gc_interval:
            log.debug("Send task GC command to {0}".format(identity))
            self._last_gc_time[identity] = t
            return "task_gc", self._get_running_tasks()
