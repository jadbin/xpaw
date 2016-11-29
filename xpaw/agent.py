# coding=utf-8

import os
import re
import json
import time
import asyncio
import logging
import sqlite3
import threading

import aiohttp
from aiohttp import web
import async_timeout

from xpaw.ds import PriorityQueue

log = logging.getLogger(__name__)


class Agent:
    def __init__(self, server_listen, *, local_config=None):
        self._server_listen = server_listen
        self._manager_loop = asyncio.new_event_loop()
        self._server_loop = asyncio.new_event_loop()
        local_config["proxy_manager_loop"] = self._manager_loop
        self._proxy_managers = ProxyManagers.from_config(local_config)
        self._is_running = False

    @classmethod
    def from_config(cls, config):
        return cls(config.get("agent_server_listen"), local_config=config)

    def start(self):
        if not self._is_running:
            self._is_running = True
            self._start_manager_loop()
            self._start_server_loop()

    def _start_server_loop(self):
        def _start():
            asyncio.set_event_loop(self._server_loop)
            try:
                self._server_loop.run_forever()
            except Exception:
                log.error("Unexpected error occurred when run loop", exc_info=True)
                raise
            finally:
                self._server_loop.close()

        log.info("Start agent server on '{0}'".format(self._server_listen))
        app = web.Application(logger=log, loop=self._server_loop)
        for i in self._proxy_managers:
            log.debug("Add route '/{0}'".format(i))
            resource = app.router.add_resource("/{0}".format(i))
            resource.add_route("GET", lambda r, i=i: self._get_proxy_list(r, i))
            resource.add_route("POST", lambda r, i=i: self._post_proxy_list(r, i))
        host, port = self._server_listen.split(":")
        port = int(port)
        self._server_loop.run_until_complete(
            self._server_loop.create_server(app.make_handler(access_log=None), host, port))
        _start()

    def _start_manager_loop(self):
        def _start():
            asyncio.set_event_loop(self._manager_loop)
            try:
                self._manager_loop.run_forever()
            except Exception:
                log.error("Unexpected error occurred when run loop", exc_info=True)
                raise
            finally:
                self._manager_loop.close()

        for manager in self._proxy_managers.values():
            asyncio.ensure_future(manager.check_proxy(), loop=self._manager_loop)
        t = threading.Thread(target=_start, daemon=True)
        t.start()

    async def _get_proxy_list(self, request, id_string):
        """
        Get HTTP proxy list.

        :param aiohttp.web.web_reqrep.Request request: HTTP request
        """
        params = request.GET
        count = params.get("count", 0)
        if count:
            count = int(count)
        detail = "detail" in params
        host = None
        peername = request.transport.get_extra_info("peername")
        if peername:
            host, _ = peername
        log.debug("'{0}' request '/{1}', count={2}, detail={3}".format(host, id_string, count, detail))
        proxy_list = self._proxy_managers[id_string].get_proxy_list(count, detail=detail)
        return web.Response(body=json.dumps(proxy_list).encode("utf-8"),
                            charset="utf-8",
                            content_type="application/json")

    async def _post_proxy_list(self, request, id_string):
        """
        Post HTTP proxy list.

        :param aiohttp.web.web_reqrep.Request request: HTTP request
        """
        body = await request.read()
        addr_list = json.loads(body.decode("utf-8"))
        host = None
        peername = request.transport.get_extra_info("peername")
        if peername:
            host, _ = peername
        log.debug("'{0}' post {1} proxies to '/{2}'".format(host, len(addr_list), id_string))
        self._proxy_managers[id_string].add_proxy(*addr_list)
        return web.Response(status=200)


class ProxyManagers(dict):
    @classmethod
    def from_config(cls, config):
        managers = {}
        m = config.get("proxy_checkers")
        if m:
            loop = config.get("proxy_manager_loop")
            if not loop:
                loop = asyncio.get_event_loop()
            semaphore = asyncio.Semaphore(config.get("proxy_checker_clients", 100), loop=loop)
            for k, v in m.items():
                v["loop"] = loop
                v["semaphore"] = semaphore
                config["proxy_checker"] = ProxyChecker.from_config(v)
                config["proxy_db"] = ProxyDb(os.path.join(config.get("data_dir") or ".", "proxy-db", k))
                managers[k] = ProxyManager.from_config(config)
        return cls(managers)


class ProxyManager:
    def __init__(self, checker, proxy_db, *,
                 queue_size=500, backup_size=10000,
                 check_interval=300, block_time=7200, fail_times=3,
                 sleep_time=5, loop=None):
        self._checker = checker
        self._proxy_db = proxy_db
        self._check_interval = check_interval
        self._block_time = block_time
        self._fail_times = fail_times
        self._sleep_time = sleep_time
        self._data_lock = threading.Lock()
        self._loop = loop or asyncio.get_event_loop()
        self._time_line = PriorityQueue(queue_size + backup_size)
        self._proxy_list = PriorityQueue(queue_size)
        self._queue = PriorityQueue(queue_size)
        self._backup = PriorityQueue(backup_size)

    @classmethod
    def from_config(cls, config):
        kw = {}
        if "proxy_queue_size" in config:
            kw["queue_size"] = config["proxy_queue_size"]
        if "proxy_backup_size" in config:
            kw["backup_size"] = config["proxy_backup_size"]
        if "proxy_check_interval" in config:
            kw["check_interval"] = config["proxy_check_interval"]
        if "proxy_block_time" in config:
            kw["block_time"] = config["proxy_block_time"]
        if "proxy_fail_times" in config:
            kw["proxy_fail_times"] = config["proxy_fail_times"]
        if "checker_sleep_time" in config:
            kw["sleep_time"] = config["checker_sleep_time"]
        kw["loop"] = config.get("proxy_manager_loop")
        return cls(config.get("proxy_checker"), config.get("proxy_db"), **kw)

    def get_proxy_list(self, count, *, detail=False):
        res = []
        with self._data_lock:
            total = len(self._queue)
            if not count or total < count:
                count = total
            t = []
            i = 1
            while i <= count:
                proxy = self._proxy_list.top()
                del self._proxy_list[proxy.queue_index]
                del self._queue[proxy.queue_index]
                t.append(proxy)
                if detail:
                    res.append({"addr": proxy.addr, "success": proxy.good, "fail": proxy.bad})
                else:
                    res.append(proxy.addr)
                i += 1
            for proxy in t:
                i = self._queue.push(proxy, (-proxy.rate, -proxy.timestamp))
                self._proxy_list.push(proxy, (proxy.rate, proxy.timestamp))
                proxy.queue_index = i
        return res

    def add_proxy(self, *addr_list):
        with self._data_lock:
            t = int(time.time())
            for addr in addr_list:
                try:
                    proxy = self._proxy_db.find_proxy(addr)
                    if proxy and t - proxy.timestamp <= self._block_time:
                        continue
                    proxy = ProxyInfo(addr, t)
                    self._proxy_db.update_timestamp(proxy)
                    if self._backup.is_full():
                        p = self._backup.top()
                        if (proxy.rate, -proxy.fail) >= (p.rate, -p.fail):
                            self._pop_backup(p)
                            self._push_backup(proxy)
                    else:
                        self._push_backup(proxy)
                except Exception:
                    log.warning("Unexpected error occurred when add proxy '{0}'".format(addr), exc_info=True)

    async def check_proxy(self):
        while True:
            proxy = None
            t = int(time.time())
            with self._data_lock:
                if len(self._time_line) > 0:
                    p = self._time_line.top()
                    if t > p.timestamp:
                        if p.status == p.IN_QUEUE:
                            self._pop_queue(p)
                        elif p.status == p.IN_BACKUP:
                            self._pop_backup(p)
                        proxy = p
            if proxy is not None:
                await self._checker.check_proxy(proxy.addr, lambda ok, proxy=proxy: self._handle_result(proxy, ok))
            else:
                await asyncio.sleep(self._sleep_time, loop=self._loop)

    def _handle_result(self, proxy, ok):
        with self._data_lock:
            t = int(time.time())
            proxy.timestamp = t + self._check_interval
            self._proxy_db.update_timestamp(proxy)
            if ok:
                proxy.good += 1
                proxy.fail = 0
                if self._queue.is_full():
                    p = self._queue.top()
                    if proxy.rate > p.rate:
                        self._pop_queue(p)
                        self._push_queue(proxy)
                        proxy = p
                else:
                    self._push_queue(proxy)
                    proxy = None
            else:
                proxy.bad += 1
                proxy.fail += 1
                if proxy.fail > self._fail_times:
                    proxy = None
            if proxy is not None:
                if self._backup.is_full():
                    p = self._backup.top()
                    if (proxy.rate, -proxy.fail) > (p.rate, -p.fail):
                        self._pop_backup(p)
                        self._push_backup(proxy)
                else:
                    self._push_backup(proxy)

    def _push_queue(self, proxy):
        proxy.line_index = self._time_line.push(proxy, -proxy.timestamp)
        proxy.queue_index = self._queue.push(proxy, (-proxy.rate, -proxy.timestamp))
        self._proxy_list.push(proxy, (proxy.rate, proxy.timestamp))
        proxy.status = proxy.IN_QUEUE

    def _pop_queue(self, proxy):
        del self._time_line[proxy.line_index]
        del self._queue[proxy.queue_index]
        del self._proxy_list[proxy.queue_index]
        proxy.status = None

    def _push_backup(self, proxy):
        proxy.line_index = self._time_line.push(proxy, -proxy.timestamp)
        proxy.queue_index = self._backup.push(proxy, (-proxy.rate, proxy.fail))
        proxy.status = proxy.IN_BACKUP

    def _pop_backup(self, proxy):
        del self._time_line[proxy.line_index]
        del self._backup[proxy.queue_index]
        proxy.status = None


class ProxyChecker:
    def __init__(self, url, *, http_status=200, url_match=None, body_match=None, timeout=10, loop=None, semaphore=None):
        self._url = url
        self._http_status = http_status
        self._url_match = url_match
        self._body_match = body_match
        self._timeout = timeout
        self._loop = loop or asyncio.get_event_loop()
        self._semaphore = semaphore

    @classmethod
    def from_config(cls, config):
        kw = {}
        if "response" in config:
            resp = config["response"]
            if "http_status" in resp:
                kw["http_status"] = resp["http_status"]
            if "url_match" in resp:
                kw["url_match"] = re.compile(resp["url_match"])
            if "body_match" in resp:
                if "encoding" in resp:
                    encoding = resp["encoding"]
                else:
                    encoding = "utf-8"
                kw["body_match"] = re.compile(resp["body_match"].encode(encoding))
        if "timeout" in config:
            kw["timeout"] = config["timeout"]
        kw["loop"] = config.get("loop")
        kw["semaphore"] = config.get("semaphore")
        return cls(config.get("url"), **kw)

    async def check_proxy(self, addr, callback):
        async def _check():
            if not addr.startswith("http://"):
                proxy = "http://{0}".format(addr)
            else:
                proxy = addr
            try:
                with aiohttp.ClientSession(loop=self._loop) as session:
                    with async_timeout.timeout(self._timeout, loop=self._loop):
                        async with session.request("GET", self._url, proxy=proxy) as resp:
                            if resp.status != self._http_status:
                                return False
                            if self._url_match and not self._url_match.search(resp.url):
                                return False
                            body = await resp.read()
                            if self._body_match and not self._body_match.search(body):
                                return False
            except Exception:
                return False
            return True

        async def _task():
            ok = await _check()
            try:
                callback(ok)
            except Exception:
                log.warning("Unexpected error occurred in callback", exc_info=True)
            finally:
                if self._semaphore:
                    self._semaphore.release()

        if self._semaphore:
            await self._semaphore.acquire()
        asyncio.ensure_future(_task(), loop=self._loop)


class ProxyDb:
    COMMIT_COUNT = 1000
    TBL_NAME = "http_proxy"

    def __init__(self, db_file):
        db_file = os.path.abspath(db_file)
        log.debug("Load proxy database '{0}'".format(db_file))
        db_dir = os.path.dirname(db_file)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, mode=0o775)
        self._conn = sqlite3.connect(db_file, check_same_thread=False)
        self._create_table()
        self._update_count = 0

    def _create_table(self):
        self._conn.execute("DROP TABLE IF EXISTS {0}".format(self.TBL_NAME))
        self._conn.execute("""CREATE TABLE {0} (
              addr TEXT NOT NULL,
              timestamp INTEGER DEFAULT 0,
              PRIMARY KEY(addr))""".format(self.TBL_NAME))
        self._conn.commit()

    def find_proxy(self, addr):
        """
        Find the HTTP proxy information according to the proxy address.

        :param str addr: proxy address
        :return: proxy information
        :rtype: None or xpaw.agent.ProxyInfo
        """
        res = None
        cursor = self._conn.cursor()
        try:
            cursor.execute("SELECT * FROM {0} WHERE addr='{1}'".format(self.TBL_NAME, addr))
            line = cursor.fetchone()
            if line:
                res = ProxyInfo(*line)
        except Exception:
            raise
        finally:
            cursor.close()
        return res

    def update_timestamp(self, proxy):
        """
        Update the HTTP proxy information in the database.

        :param xpaw.agent.ProxyInfo proxy: proxy information
        """
        self._conn.execute(
            "REPLACE INTO {0} (addr, timestamp) VALUES ('{1}', {2})".format(self.TBL_NAME, proxy.addr, proxy.timestamp))
        self._update_count += 1
        if self._update_count >= self.COMMIT_COUNT:
            self._conn.commit()
            self._update_count = 0


class ProxyInfo:
    IN_QUEUE = 1
    IN_BACKUP = 2

    def __init__(self, addr, timestamp):
        self.addr = addr
        self.timestamp = timestamp
        self.good = 0
        self.bad = 0
        self.fail = 1
        self.status = None
        self.line_index = None
        self.queue_index = None

    @property
    def rate(self):
        return self.good / (self.good + self.bad + 1.0)
