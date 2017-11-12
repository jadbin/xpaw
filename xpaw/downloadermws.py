# coding=utf-8

import json
import random
import logging
import asyncio
from asyncio import CancelledError

import aiohttp
from yarl import URL

from .errors import IgnoreRequest, NetworkError, NotEnabled
from .utils import parse_url

log = logging.getLogger(__name__)


class RetryMiddleware:
    RETRY_ERRORS = (NetworkError,)

    def __init__(self, config):
        if not config.getbool('retry_enabled'):
            raise NotEnabled
        self._max_retry_times = config.getint('max_retry_times')
        self._http_status = config.getlist('retry_http_status')

    @classmethod
    def from_cluster(cls, cluster):
        return cls(cluster.config)

    def handle_response(self, request, response):
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
            for i in range(n):
                if pattern[i] != "x" and pattern[i] != "X" and pattern[i] != s[i]:
                    match = False
                    break
        if verse:
            match = not match
        return match

    def handle_error(self, request, error):
        if isinstance(error, self.RETRY_ERRORS):
            return self.retry(request, "{}: {}".format(type(error).__name__, error))

    def retry(self, request, reason):
        retry_times = request.meta.get("retry_times", 0) + 1
        if retry_times <= self._max_retry_times:
            log.debug("We will retry the request (url=%s) because of %s", request.url, reason)
            retry_req = request.copy()
            retry_req.meta["retry_times"] = retry_times
            retry_req.dont_filter = True
            return retry_req
        else:
            log.info("The request (url=%s) has been retried %s times,"
                     " and it will be aborted", request.url, self._max_retry_times)
            raise IgnoreRequest


class DefaultHeadersMiddleware:
    def __init__(self, config):
        self._headers = config.get("default_headers")
        if self._headers is None:
            raise NotEnabled

    @classmethod
    def from_cluster(cls, cluster):
        return cls(cluster.config)

    def handle_request(self, request):
        for h in self._headers:
            request.headers.setdefault(h, self._headers[h])


class ImitatingProxyMiddleware:
    def __init__(self, config):
        if not config.getbool('imitating_proxy_enabled'):
            raise NotEnabled

    @classmethod
    def from_cluster(cls, cluster):
        return cls(cluster.config)

    def handle_request(self, request):
        ip = "61.%s.%s.%s" % (random.randint(128, 191), random.randint(0, 255), random.randint(1, 254))
        request.headers.setdefault('X-Forwarded-For', ip)
        request.headers.setdefault('Via', '1.1 xpaw')


class ProxyMiddleware:
    UPDATE_INTERVAL = 60
    TIMEOUT = 20

    def __init__(self, config, loop=None):
        self._proxies = {'http': [], 'https': []}
        proxy = config.getlist('proxy', [])
        proxy_agent = config.get('proxy_agent')
        if not proxy and not proxy_agent:
            raise NotEnabled
        for p in proxy:
            self._append_proxy(p)
        self._agent_addr = parse_url(proxy_agent)
        self._loop = loop or asyncio.get_event_loop()
        self._update_lock = asyncio.Lock(loop=self._loop)
        self._update_future = None

    @classmethod
    def from_cluster(cls, cluster):
        return cls(cluster.config, loop=cluster.loop)

    async def handle_request(self, request):
        if isinstance(request.url, str):
            url = URL(request.url)
        else:
            url = request.url
        proxy = await self.get_proxy(url.scheme)
        if proxy:
            addr, auth = proxy
            request.proxy = addr
            request.proxy_auth = auth

    async def get_proxy(self, scheme):
        if scheme not in self._proxies:
            return
        if self._agent_addr:
            async with self._update_lock:
                if len(self._proxies[scheme]) <= 0:
                    await self._update_proxy_list()
        n = len(self._proxies[scheme])
        if n > 0:
            return random.choice(self._proxies[scheme])

    def _append_proxy(self, p):
        addr, auth, scheme = None, None, None
        if isinstance(p, str):
            addr = p
        elif isinstance(p, dict):
            addr = p.get('addr')
            auth = p.get('auth')
            scheme = p.get('scheme')
        if addr:
            if scheme:
                schemes = scheme.split(',')
                for s in schemes:
                    if s in self._proxies:
                        self._proxies[s].append((addr, auth))
            else:
                self._proxies['http'].append((addr, auth))
                self._proxies['https'].append((addr, auth))

    async def _update_proxy_list(self):
        try:
            async with aiohttp.ClientSession(loop=self._loop) as session:
                with aiohttp.Timeout(self.TIMEOUT, loop=self._loop):
                    async with session.get(self._agent_addr) as resp:
                        body = await resp.read()
                        proxy_list = json.loads(body.decode(encoding="utf-8"))
                        if proxy_list:
                            for k in self._proxies:
                                self._proxies[k].clear()
                            for p in proxy_list:
                                self._append_proxy(p)
        except CancelledError:
            raise
        except Exception:
            log.warning("Error occurred when updated proxy list", exc_info=True)

    async def _update_proxy_list_task(self):
        while True:
            async with self._update_lock:
                await self._update_proxy_list()
            await asyncio.sleep(self.UPDATE_INTERVAL, loop=self._loop)

    def open(self):
        if self._agent_addr:
            self._update_future = asyncio.ensure_future(self._update_proxy_list_task(), loop=self._loop)

    def close(self):
        if self._update_future:
            self._update_future.cancel()


class SpeedLimitMiddleware:
    def __init__(self, config, loop=None):
        self._rate = config.getint('speed_limit_rate')
        if self._rate is None:
            raise NotEnabled
        if self._rate <= 0:
            raise ValueError("rate must be greater than 0")
        self._burst = config.getint('speed_limit_burst', config.getint('downloader_clients'))
        if self._burst <= 0:
            raise ValueError('burst must be greater than 0')
        self._interval = 1.0 / self._rate
        self._bucket = self._burst
        self._loop = loop or asyncio.get_event_loop()
        self._semaphore = asyncio.Semaphore(self._burst, loop=loop)
        self._update_future = None

    @classmethod
    def from_cluster(cls, cluster):
        return cls(cluster.config, loop=cluster.loop)

    async def handle_request(self, request):
        await self._semaphore.acquire()
        self._bucket -= 1

    async def _update_value(self):
        while True:
            await asyncio.sleep(self._interval, loop=self._loop)
            if self._bucket + 1 <= self._burst:
                self._bucket += 1
                self._semaphore.release()

    def open(self):
        self._update_future = asyncio.ensure_future(self._update_value(), loop=self._loop)

    def close(self):
        if self._update_future:
            self._update_future.cancel()


class UserAgentMiddleware:
    DEVICE_TYPE = {'desktop', 'mobile'}
    BROWSER_TYPE = {'chrome'}

    def __init__(self, config):
        ua = config.get('user_agent')
        self._random = config.getbool('random_user_agent')
        if not ua and not self._random:
            raise NotEnabled
        self._device_type = 'desktop'
        self._browser = 'chrome'
        self._user_agent = None
        if ua:
            self._configure_user_agent(ua)

    @classmethod
    def from_cluster(cls, cluster):
        return cls(cluster.config)

    def handle_request(self, request):
        if self._random:
            user_agent = self._gen_user_agent(self._device_type, self._browser)
        else:
            user_agent = self._user_agent
        request.headers.setdefault('User-Agent', user_agent)

    def _configure_user_agent(self, ua):
        if not ua.startswith(':'):
            self._user_agent = ua
            return
        s = ua[1:].split(',')
        s.reverse()
        for i in s:
            if i in self.DEVICE_TYPE:
                self._device_type = i
            elif i in self.BROWSER_TYPE:
                self._browser = i
            else:
                raise ValueError('Unknown user agent description: {}'.format(i))
        self._user_agent = self._gen_user_agent(self._device_type, self._browser)

    @staticmethod
    def _gen_user_agent(device, browser):
        if browser == 'chrome':
            chrome_version = '{}.0.{}.{}'.format(random.randint(50, 60),
                                                 random.randint(0, 2999), random.randint(0, 99))
            webkit = '{}.{}'.format(random.randint(531, 600), random.randint(0, 99))
            if device == 'desktop':
                os = 'Macintosh; Intel Mac OS X 10_10_4'
                return ('Mozilla/5.0 ({}) AppleWebKit/{} (KHTML, like Gecko) '
                        'Chrome/{} Safari/{}').format(os, webkit, chrome_version, webkit)
            elif device == 'mobile':
                os = 'iPhone; CPU iPhone OS 10_3 like Mac OS X'
                mobile = '14E{:03d}'.format(random.randint(0, 999))
                return ('Mozilla/5.0 ({}) AppleWebKit/{} (KHTML, like Gecko) '
                        'CriOS/{} Mobile/{} Safari/{}').format(os, webkit, chrome_version, mobile, webkit)
