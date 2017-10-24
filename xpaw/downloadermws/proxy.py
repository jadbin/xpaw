# coding=utf-8

import json
import random
import asyncio
import logging

import aiohttp
import async_timeout

log = logging.getLogger(__name__)


class ProxyMiddleware:
    def __init__(self, proxies):
        if not proxies or len(proxies) <= 0:
            raise ValueError("proxies cannot be empty")
        self._proxies = proxies
        self._n = len(proxies)

    @classmethod
    def from_config(cls, config):
        return cls(config.getlist("proxies"))

    async def handle_request(self, request):
        proxy = self._pick_proxy()
        log.debug("Assign proxy '{}' to request (url={})".format(proxy, request.url))
        if not proxy.startswith("http://"):
            proxy = "http://{}".format(proxy)
        request.proxy = proxy

    def _pick_proxy(self):
        i = random.randint(0, self._n - 1)
        return self._proxies[i]


class ProxyAgentMiddleware:
    def __init__(self, agent_addr, *, update_interval=60, timeout=20, loop=None):
        if not agent_addr.startswith("http://") and not agent_addr.startswith("https://"):
            agent_addr = "http://{}".format(agent_addr)
        self._agent_addr = agent_addr
        self._update_interval = update_interval
        self._timeout = timeout
        self._loop = loop or asyncio.get_event_loop()
        self._proxy_list = []
        self._update_lock = asyncio.Lock(loop=self._loop)
        self._update_future = None

    @classmethod
    def from_config(cls, config):
        c = config.get("proxy_agent")
        if c is None:
            c = {}
        return cls(**c, loop=config.get("downloader_loop"))

    async def handle_request(self, request):
        proxy = await self.get_proxy()
        log.debug("Assign proxy '{}' to request (url={})".format(proxy, request.url))
        if not proxy.startswith("http://"):
            proxy = "http://{}".format(proxy)
        request.proxy = proxy

    async def get_proxy(self):
        while True:
            async with self._update_lock:
                if not self._proxy_list:
                    await self.update_proxy_list()
                if self._proxy_list:
                    break
            await asyncio.sleep(self._timeout, loop=self._loop)
        return self._proxy_list[random.randint(0, len(self._proxy_list) - 1)]

    async def update_proxy_list(self):
        log.debug("Update proxy list")
        try:
            async with aiohttp.ClientSession(loop=self._loop) as session:
                with async_timeout.timeout(self._timeout, loop=self._loop):
                    async with session.get(self._agent_addr) as resp:
                        body = await resp.read()
                        proxy_list = json.loads(body.decode(encoding="utf-8"))
                        if proxy_list:
                            self._proxy_list = proxy_list
        except Exception:
            log.warning("Error occurred when update proxy list", exc_info=True)

    async def _update_proxy_list_task(self):
        while True:
            async with self._update_lock:
                await self.update_proxy_list()
            await asyncio.sleep(self._update_interval, loop=self._loop)

    def open(self):
        self._update_future = asyncio.ensure_future(self._update_proxy_list_task(), loop=self._loop)

    def close(self):
        if self._update_future:
            self._update_future.cancel()
