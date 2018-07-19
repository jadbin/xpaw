# coding=utf-8

import random
import logging
import asyncio
from os.path import join, isfile
import pickle

import aiohttp
from yarl import URL

from .errors import IgnoreRequest, NetworkError, NotEnabled
from .version import __version__
from . import utils

log = logging.getLogger(__name__)


class RetryMiddleware:
    RETRY_ERRORS = (NetworkError,)

    def __init__(self, max_retry_times, retry_http_status=None):
        self._max_retry_times = max_retry_times
        self._http_status = retry_http_status or []

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}(max_retry_times={}, retry_http_status={})' \
            .format(cls_name, repr(self._max_retry_times), repr(self._http_status))

    @classmethod
    def from_cluster(cls, cluster):
        config = cluster.config
        if not config.getbool('retry_enabled'):
            raise NotEnabled
        return cls(max_retry_times=config.getint('max_retry_times'),
                   retry_http_status=config.getlist('retry_http_status'))

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
            return self.retry(request, str(error))

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
            raise IgnoreRequest(reason)


class DefaultHeadersMiddleware:
    def __init__(self, default_headers=None):
        self._headers = default_headers or {}

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}(default_headers={})'.format(cls_name, repr(self._headers))

    @classmethod
    def from_cluster(cls, cluster):
        default_headers = cluster.config.get("default_headers")
        if default_headers is None:
            raise NotEnabled
        return cls(default_headers=default_headers)

    def handle_request(self, request):
        for h in self._headers:
            request.headers.setdefault(h, self._headers[h])


class ImitatingProxyMiddleware:
    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}()'.format(cls_name)

    @classmethod
    def from_cluster(cls, cluster):
        if not cluster.config.getbool('imitating_proxy_enabled'):
            raise NotEnabled
        return cls()

    def handle_request(self, request):
        ip = '{}.{}.{}.{}'.format(random.randint(1, 126), random.randint(1, 254),
                                  random.randint(1, 254), random.randint(1, 254))
        request.headers.setdefault('X-Forwarded-For', ip)
        request.headers.setdefault('Via', '{} xpaw'.format(__version__))


class CookiesMiddleware:
    def __init__(self, dump_dir=None, loop=None):
        self._dump_dir = dump_dir
        self._loop = loop or asyncio.get_event_loop()
        self._cookie_jars = {}

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}()'.format(cls_name)

    @classmethod
    def from_cluster(cls, cluster):
        config = cluster.config
        if not config.getbool('cookie_jar_enabled'):
            raise NotEnabled
        return cls(dump_dir=utils.get_dump_dir(config), loop=cluster.loop)

    def handle_request(self, request):
        cookie_jar_key = request.meta.get('cookie_jar_key')
        if cookie_jar_key is None or isinstance(cookie_jar_key, (int, str)):
            cookie_jar = self._cookie_jars.get(cookie_jar_key)
            if cookie_jar is None:
                cookie_jar = aiohttp.CookieJar(loop=self._loop)
                self._cookie_jars[cookie_jar_key] = cookie_jar
            request.meta['cookie_jar'] = cookie_jar

    def open(self):
        if self._dump_dir:
            file = join(self._dump_dir, 'cookie_jar')
            if isfile(file):
                with open(file, 'rb') as f:
                    jars = pickle.load(f)
                    for key in jars:
                        cookie_jar = aiohttp.CookieJar(loop=self._loop)
                        cookie_jar._cookies = jars[key]
                        self._cookie_jars[key] = cookie_jar

    def close(self):
        if self._dump_dir:
            jars = {}
            for key in self._cookie_jars:
                jars[key] = self._cookie_jars[key]._cookies
            with open(join(self._dump_dir, 'cookie_jar'), 'wb') as f:
                pickle.dump(jars, f)


class ProxyMiddleware:
    def __init__(self, proxy):
        self._proxies = {'http': [], 'https': []}
        self._set_proxy(proxy)

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}(proxy={})'.format(cls_name, repr(self._proxies))

    @classmethod
    def from_cluster(cls, cluster):
        proxy = cluster.config.get('proxy')
        if not proxy:
            raise NotEnabled
        return cls(proxy=proxy)

    def handle_request(self, request):
        if isinstance(request.url, str):
            url = URL(request.url)
        else:
            url = request.url
        proxy = self.get_proxy(url.scheme)
        if proxy:
            request.meta['proxy'] = proxy

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
    def __init__(self, speed_limit_rate, speed_limit_burst, loop=None):
        self._rate = speed_limit_rate
        self._burst = speed_limit_burst
        if self._rate <= 0:
            raise ValueError("rate must be greater than 0")
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
        config = cluster.config
        if not config.getbool('speed_limit_enabled'):
            raise NotEnabled
        speed_limit_rate = config.getfloat('speed_limit_rate')
        speed_limit_burst = config.getint('speed_limit_burst')
        return cls(speed_limit_rate=speed_limit_rate, speed_limit_burst=speed_limit_burst, loop=cluster.loop)

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

    def __init__(self, user_agent, random_user_agent=False):
        self._random = random_user_agent
        self._device_type = 'desktop'
        self._browser = 'chrome'
        self._user_agent = None
        if user_agent:
            self._configure_user_agent(user_agent)

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}(user_agent={}, random_user_agent={})'.format(cls_name, repr(self._user_agent), repr(self._random))

    @classmethod
    def from_cluster(cls, cluster):
        config = cluster.config
        user_agent = config.get('user_agent')
        random_user_agent = config.getbool('random_user_agent')
        if not user_agent and not random_user_agent:
            raise NotEnabled
        return cls(user_agent=user_agent, random_user_agent=random_user_agent)

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
            chrome_version = '{}.0.{}.{}'.format(random.randint(51, 70),
                                                 random.randint(0, 9999), random.randint(0, 99))
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
