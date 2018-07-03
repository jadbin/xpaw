# coding=utf-8

import json
import random
import logging
import asyncio
from asyncio import CancelledError

import aiohttp
import async_timeout
from yarl import URL

from .errors import IgnoreRequest, NetworkError, NotEnabled
from .utils import parse_url
from .version import __version__

log = logging.getLogger(__name__)


class RetryMiddleware:
    RETRY_ERRORS = (NetworkError,)

    def __init__(self, config):
        if not config.getbool('retry_enabled'):
            raise NotEnabled
        self._max_retry_times = config.getint('max_retry_times')
        self._http_status = config.getlist('retry_http_status')

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}(max_retry_times={}, retry_http_status={})' \
            .format(cls_name, repr(self._max_retry_times), repr(self._http_status))

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
            log.debug("We will retry the request %s because of %s", request, reason)
            retry_req = request.copy()
            retry_req.meta["retry_times"] = retry_times
            retry_req.dont_filter = True
            return retry_req
        else:
            log.info("The request %s has been retried %s times,"
                     " and it will be aborted", request, self._max_retry_times)
            raise IgnoreRequest


class DefaultHeadersMiddleware:
    def __init__(self, config):
        self._headers = config.get("default_headers")
        if self._headers is None:
            raise NotEnabled

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}(default_headers={})'.format(cls_name, repr(self._headers))

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

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}()'.format(cls_name)

    @classmethod
    def from_cluster(cls, cluster):
        return cls(cluster.config)

    def handle_request(self, request):
        ip = "61.%s.%s.%s" % (random.randint(128, 191), random.randint(0, 255), random.randint(1, 254))
        request.headers.setdefault('X-Forwarded-For', ip)
        request.headers.setdefault('Via', '{} xpaw'.format(__version__))


class CookiesMiddleware:
    def __init__(self, config, loop=None):
        if not config.getbool('cookie_jar_enabled'):
            raise NotEnabled
        self._loop = loop or asyncio.get_event_loop()
        self._cookie_jars = {}

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}()'.format(cls_name)

    @classmethod
    def from_cluster(cls, cluster):
        return cls(cluster.config, loop=cluster.loop)

    def handle_request(self, request):
        cookie_jar_key = request.meta.get('cookie_jar')
        cookie_jar = self._cookie_jars.get(cookie_jar_key)
        if cookie_jar is None:
            cookie_jar = aiohttp.CookieJar(loop=self._loop)
            self._cookie_jars[cookie_jar_key] = cookie_jar
        request.cookie_jar = cookie_jar


class ProxyMiddleware:
    def __init__(self, config):
        self._proxies = {'http': [], 'https': []}
        proxy = config.get('proxy')
        if not proxy:
            raise NotEnabled
        self._set_proxy(proxy)

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}(proxy={})'.format(cls_name, repr(self._proxies))

    @classmethod
    def from_cluster(cls, cluster):
        return cls(cluster.config)

    def handle_request(self, request):
        if isinstance(request.url, str):
            url = URL(request.url)
        else:
            url = request.url
        proxy = self.get_proxy(url.scheme)
        if proxy:
            request.proxy = proxy

    def get_proxy(self, scheme):
        if scheme not in self._proxies:
            return
        if len(self._proxies[scheme]) > 0:
            return random.choice(self._proxies[scheme])

    def _set_proxy(self, proxy):
        if isinstance(proxy, (str, list, tuple)):
            self._append_proxy(proxy, 'http')
            self._append_proxy(proxy, 'https')
        elif isinstance(proxy, dict):
            self._append_proxy(proxy.get('http'), 'http')
            self._append_proxy(proxy.get('https'), 'https')

    def _append_proxy(self, proxy, scheme):
        if isinstance(proxy, str):
            self._proxies[scheme].append(proxy)
        elif isinstance(proxy, (list, tuple)):
            for p in proxy:
                self._proxies[scheme].append(p)


class SpeedLimitMiddleware:
    def __init__(self, config, loop=None):
        if not config.getbool('speed_limit_enabled'):
            raise NotEnabled
        self._rate = config.getint('speed_limit_rate')
        if self._rate <= 0:
            raise ValueError("rate must be greater than 0")
        self._burst = config.getint('speed_limit_burst')
        if self._burst <= 0:
            raise ValueError('burst must be greater than 0')
        self._interval = 1.0 / self._rate
        self._bucket = self._burst
        self._loop = loop or asyncio.get_event_loop()
        self._semaphore = asyncio.Semaphore(self._burst, loop=loop)
        self._update_future = None

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}(speed_limit_rate={}, speed_limit_burst={})'.format(cls_name, repr(self._rate), repr(self._burst))

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

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}(user_agent={}, random_user_agent={})'.format(cls_name, repr(self._user_agent), repr(self._random))

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
