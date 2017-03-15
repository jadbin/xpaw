# coding=utf-8

import json
import random
import asyncio
import logging

import aiohttp
import async_timeout

log = logging.getLogger(__name__)


class ProxyAgentMiddleware:
    def __init__(self, agent_addr, update_interval, *, update_timeout=20, loop=None):
        if not agent_addr.startswith("http://"):
            agent_addr = "http://{}".format(agent_addr)
        self._agent_addr = agent_addr
        self._update_interval = update_interval
        self._update_timeout = update_timeout
        self._loop = loop or asyncio.get_event_loop()
        self._proxy_list = None
        self._update_slot = 1
        self._update_lock = asyncio.Lock(loop=self._loop)

    @classmethod
    def from_config(cls, config):
        kw = {}
        if "proxy_update_timeout" in config:
            kw["update_timeout"] = config["proxy_update_timeout"]
        return cls(config.get("proxy_agent_addr"),
                   config.get("proxy_update_interval", 30),
                   **kw,
                   loop=config.get("downloader_loop"))

    async def handle_request(self, request):
        proxy = await self._pick_proxy()
        log.debug("Assign proxy '{}' to request (url={})".format(proxy, request.url))
        if not proxy.startswith("http://"):
            proxy = "http://{}".format(proxy)
        request.proxy = proxy

    async def _pick_proxy(self):
        while True:
            await self._update_proxy_list()
            if self._proxy_list:
                break
            await asyncio.sleep(self._update_interval, loop=self._loop)
        n = len(self._proxy_list)
        i = random.randint(0, n - 1)
        return self._proxy_list[i]

    async def _update_proxy_list(self):
        async with self._update_lock:
            if self._update_slot > 0:
                self._update_slot -= 1
                log.debug("Update proxy list")
                try:
                    async with aiohttp.ClientSession(loop=self._loop) as session:
                        with async_timeout.timeout(self._update_timeout, loop=self._loop):
                            async with session.get(self._agent_addr) as resp:
                                body = await resp.read()
                                proxy_list = json.loads(body.decode(encoding="utf-8"))
                                if proxy_list:
                                    self._proxy_list = proxy_list
                except Exception:
                    log.warning("Unexpected error occurred when updating proxy list", exc_info=True)
                finally:
                    asyncio.ensure_future(self._update_slot_delay(), loop=self._loop)

    async def _update_slot_delay(self):
        await asyncio.sleep(self._update_interval, loop=self._loop)
        async with self._update_lock:
            self._update_slot += 1
