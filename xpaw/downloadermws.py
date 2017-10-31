# coding=utf-8

import re
import json
import random
import logging
import asyncio

import aiohttp
from yarl import URL

from .errors import ResponseNotMatch, IgnoreRequest, NetworkError
from .utils import parse_url

log = logging.getLogger(__name__)


class RetryMiddleware:
    RETRY_ERRORS = (NetworkError, ResponseNotMatch)
    RETRY_HTTP_STATUS = (500, 502, 503, 504, 408)

    def __init__(self, max_retry_times=3, http_status=RETRY_HTTP_STATUS):
        self._max_retry_times = max_retry_times
        self._http_status = http_status

    @classmethod
    def from_cluster(cls, cluster):
        c = cluster.config.get("retry")
        if c is None:
            c = {}
        return cls(**c)

    async def handle_response(self, request, response):
        for p in self._http_status:
            if self.match_status(p, response.status):
                return self.retry(request, "http status={}".format(response.status))

    @staticmethod
    def match_status(pattern, status):
        if isinstance(pattern, int):
            return pattern == status
        verse = False
        if pattern.startswith("!") or pattern.startswith("~"):
            verse = True
            pattern = pattern[1:]
        s = str(status)
        n = len(s)
        match = True
        if len(pattern) != n:
            match = False
        else:
            i = 0
            while i < n:
                if pattern[i] != "x" and pattern[i] != "X" and pattern[i] != s[i]:
                    match = False
                    break
                i += 1
        if verse:
            match = not match
        return match

    async def handle_error(self, request, error):
        if isinstance(error, self.RETRY_ERRORS):
            return self.retry(request, "{}: {}".format(type(error).__name__, error))

    def retry(self, request, reason):
        retry_times = request.meta.get("retry_times", 0) + 1
        if retry_times <= self._max_retry_times:
            log.debug("We will retry the request(url={}) because of {}".format(request.url, reason))
            retry_req = request.copy()
            retry_req.meta["retry_times"] = retry_times
            retry_req.dont_filter = True
            return retry_req
        else:
            log.info("The request(url={}) has been retried {} times,"
                     " and it will be aborted.".format(request.url, self._max_retry_times))
            raise IgnoreRequest


class ResponseMatchMiddleware:
    def __init__(self, patterns):
        self._patterns = patterns

    @classmethod
    def from_cluster(cls, cluster):
        c = cluster.config.getlist("response_match")
        return cls([_ResponseMatchPattern(i.get("url_pattern"),
                                          i.get("body_pattern"),
                                          i.get("encoding"))
                    for i in c])

    async def handle_response(self, request, response):
        for p in self._patterns:
            if p.not_match(request, response):
                raise ResponseNotMatch("Response body does not fit the pattern")


class _ResponseMatchPattern:
    def __init__(self, url_pattern, body_pattern, encoding):
        if not url_pattern:
            raise ValueError("url pattern is none")
        if not body_pattern:
            raise ValueError("body pattern is none")
        self._url_pattern = re.compile(url_pattern)
        self._body_pattern = re.compile(body_pattern)
        self._encoding = encoding

    def not_match(self, request, response):
        req_url = str(request.url)
        if response.body:
            if self._url_pattern.search(req_url):
                if self._encoding:
                    text = response.body.decode(self._encoding, errors="replace")
                else:
                    text = response.text
                if not self._body_pattern.search(text):
                    return True
        return False


class DefaultHeadersMiddleware:
    def __init__(self, headers):
        self._headers = headers or {}

    @classmethod
    def from_cluster(cls, cluster):
        return cls(cluster.config.get("default_headers"))

    async def handle_request(self, request):
        log.debug("Assign headers to request (url={}): {}".format(request.url, self._headers))
        for h in self._headers:
            request.headers.setdefault(h, self._headers[h])


class ForwardedForMiddleware:
    async def handle_request(self, request):
        x = "61.%s.%s.%s" % (random.randint(128, 191), random.randint(0, 255), random.randint(1, 254))
        log.debug("Assign 'X-Forwarded-For: {}' to request (url={})".format(x, request.url))
        request.headers["X-Forwarded-For"] = x


class ProxyMiddleware:
    def __init__(self, request_proxy=None):
        self._proxies = {'http': [], 'https': []}
        if request_proxy:
            for p in request_proxy:
                addr, auth, scheme = None, None, None
                if isinstance(p, str):
                    addr = p
                elif isinstance(p, dict):
                    addr = p.get('addr')
                    auth = p.get('auth')
                    scheme = p.get('scheme')
                if addr:
                    if scheme:
                        if scheme in self._proxies:
                            self._proxies[scheme].append((addr, auth))
                    else:
                        self._proxies['http'].append((addr, auth))
                        self._proxies['https'].append((addr, auth))

    @classmethod
    def from_cluster(cls, cluster):
        c = cluster.config.getlist("request_proxy")
        return cls(c)

    async def handle_request(self, request):
        if isinstance(request.url, str):
            url = URL(request.url)
        else:
            url = request.url
        proxy = self._get_proxy(url.scheme)
        if proxy:
            addr, auth = proxy
            log.debug("Assign proxy '{}' to request (url={})".format(addr, request.url))
            request.proxy = addr
            request.proxy_auth = auth

    def _get_proxy(self, scheme):
        if scheme not in self._proxies:
            return
        n = len(self._proxies[scheme])
        if n > 0:
            return self._proxies[scheme][random.randint(0, n - 1)]

    def _parse_proxy(self, p):
        if isinstance(p, str):
            return p, None
        if isinstance(p, dict):
            return p.get('addr'), p.get('auth')


class ProxyAgentMiddleware:
    def __init__(self, agent_addr, *, update_interval=60, timeout=20, loop=None):
        self._agent_addr = parse_url(agent_addr)
        self._update_interval = update_interval
        self._timeout = timeout
        self._loop = loop or asyncio.get_event_loop()
        self._proxy_list = []
        self._update_lock = asyncio.Lock(loop=self._loop)
        self._update_future = None

    @classmethod
    def from_cluster(cls, cluster):
        c = cluster.config.get("proxy_agent")
        if c is None:
            c = {}
        return cls(**c, loop=cluster.loop)

    async def handle_request(self, request):
        proxy = await self.get_proxy()
        log.debug("Assign proxy '{}' to request (url={})".format(proxy, request.url))
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
                with aiohttp.Timeout(self._timeout, loop=self._loop):
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


class SpeedLimitMiddleware:
    def __init__(self, span=1, burst=1, loop=None):
        if span <= 0:
            raise ValueError("span must greater than 0")
        self._span = span
        self._burst = burst
        self._loop = loop or asyncio.get_event_loop()
        self._semaphore = asyncio.Semaphore(0, loop=loop)
        self._value = 0
        self._update_future = None

    @classmethod
    def from_cluster(cls, cluster):
        c = cluster.config.get("speed_limit")
        if c is None:
            c = {}
        return cls(**c, loop=cluster.loop)

    async def handle_request(self, request):
        await self._semaphore.acquire()
        self._value -= 1

    async def _update_value(self):
        while True:
            d = self._burst - self._value
            if d > 0:
                log.debug("Update speed limit semaphore +{}".format(d))
                self._value += d
                i = 0
                while i < d:
                    self._semaphore.release()
                    i += 1
            await asyncio.sleep(self._span, loop=self._loop)

    def open(self):
        self._update_future = asyncio.ensure_future(self._update_value(), loop=self._loop)

    def close(self):
        if self._update_future:
            self._update_future.cancel()
