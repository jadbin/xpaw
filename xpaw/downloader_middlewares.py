# coding=utf-8

import random
import logging
import asyncio
from urllib.parse import urlsplit

from .errors import ClientError, NotEnabled, HttpError
from . import __version__
from .utils import with_not_none_params

log = logging.getLogger(__name__)


class RetryMiddleware:
    RETRY_ERRORS = (ClientError,)
    RETRY_HTTP_STATUS = (500, 502, 503, 504, 408, 429)

    def __init__(self, max_retry_times=3, retry_http_status=None):
        self._max_retry_times = max_retry_times
        self._retry_http_status = retry_http_status or self.RETRY_HTTP_STATUS

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}(max_retry_times={}, retry_http_status={})' \
            .format(cls_name, repr(self._max_retry_times), repr(self._retry_http_status))

    @classmethod
    def from_crawler(cls, crawler):
        config = crawler.config
        if not config.getbool('retry_enabled'):
            raise NotEnabled
        return cls(**with_not_none_params(max_retry_times=config.getint('max_retry_times'),
                                          retry_http_status=config.getlist('retry_http_status')))

    def handle_response(self, request, response):
        for p in self._retry_http_status:
            if self.match_status(p, response.status):
                return self.retry(request, "HTTP status={}".format(response.status))

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
            return self.retry(request, error)
        if isinstance(error, HttpError):
            for p in self._retry_http_status:
                if self.match_status(p, error.response.status):
                    return self.retry(request, "HTTP status={}".format(error.response.status))

    def retry(self, request, reason):
        retry_times = request.meta.get('retry_times', 0) + 1
        if retry_times <= self._max_retry_times:
            log.debug('Retry %s (failed %s times): %s', request, retry_times, reason)
            retry_req = request.copy()
            retry_req.meta['retry_times'] = retry_times
            retry_req.dont_filter = True
            return retry_req
        else:
            log.debug('Give up retrying %s (failed %s times): %s', request, retry_times, reason)


class DefaultHeadersMiddleware:
    def __init__(self, default_headers=None):
        self._headers = default_headers or {}

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}(default_headers={})'.format(cls_name, repr(self._headers))

    @classmethod
    def from_crawler(cls, crawler):
        default_headers = crawler.config.get("default_headers")
        if default_headers is None:
            raise NotEnabled
        return cls(default_headers=default_headers)

    def handle_request(self, request):
        for k, v in self._headers.items():
            request.headers.setdefault(k, v)


class ProxyMiddleware:
    def __init__(self, proxy):
        self._proxies = {'http': None, 'https': None}
        self._set_proxy(proxy)

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}(proxy={})'.format(cls_name, repr(self._proxies))

    @classmethod
    def from_crawler(cls, crawler):
        proxy = crawler.config.get('proxy')
        if not proxy:
            raise NotEnabled
        return cls(proxy=proxy)

    def handle_request(self, request):
        if request.proxy is None:
            s = urlsplit(request.url)
            scheme = s.scheme or 'http'
            request.proxy = self._proxies.get(scheme)

    def _set_proxy(self, proxy):
        if isinstance(proxy, str):
            self._proxies['http'] = proxy
            self._proxies['https'] = proxy
        elif isinstance(proxy, dict):
            self._proxies.update(proxy)

    def _append_proxy(self, proxy, scheme):
        if isinstance(proxy, str):
            self._proxies[scheme].append(proxy)
        elif isinstance(proxy, (list, tuple)):
            for p in proxy:
                self._proxies[scheme].append(p)


class SpeedLimitMiddleware:
    def __init__(self, rate=1, burst=1):
        self._rate = rate
        self._burst = burst
        if self._rate <= 0:
            raise ValueError("rate must be greater than 0")
        if self._burst <= 0:
            raise ValueError('burst must be greater than 0')
        self._interval = 1.0 / self._rate
        self._bucket = self._burst
        self._semaphore = asyncio.Semaphore(self._burst)
        self._update_future = None

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}(speed_limit_rate={}, speed_limit_burst={})'.format(cls_name, repr(self._rate), repr(self._burst))

    @classmethod
    def from_crawler(cls, crawler):
        config = crawler.config
        if config['speed_limit'] is None:
            raise NotEnabled
        return cls(**config['speed_limit'])

    async def handle_request(self, request):
        await self._semaphore.acquire()
        self._bucket -= 1

    async def _update_value(self):
        while True:
            await asyncio.sleep(self._interval)
            if self._bucket + 1 <= self._burst:
                self._bucket += 1
                self._semaphore.release()

    def open(self):
        self._update_future = asyncio.ensure_future(self._update_value())

    def close(self):
        if self._update_future:
            self._update_future.cancel()


class UserAgentMiddleware:
    DEVICE_TYPE = {'desktop', 'mobile'}
    BROWSER_TYPE = {'chrome'}
    BROWSER_DEFAULT_HEADERS = {
        'chrome': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Upgrade-Insecure-Requests': '1'
        }
    }

    def __init__(self, user_agent=None, random_user_agent=False):
        self._device_type = None
        self._browser = None
        self._user_agent = self._make_user_agent(user_agent)
        self._is_random = random_user_agent

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}(user_agent={}, random_user_agent={})'.format(cls_name, repr(self._user_agent), repr(self._is_random))

    @classmethod
    def from_crawler(cls, crawler):
        config = crawler.config
        user_agent = config.get('user_agent')
        random_user_agent = config.getbool('random_user_agent')
        return cls(user_agent=user_agent, random_user_agent=random_user_agent)

    def handle_request(self, request):
        if self._is_random:
            user_agent = self._gen_user_agent(self._device_type, self._browser)
        else:
            user_agent = self._user_agent
        request.headers['User-Agent'] = user_agent
        self._set_browser_default_headers(request)

    def _make_user_agent(self, ua):
        if ua and ua.startswith(':'):
            for i in ua[1:].split(','):
                if i in self.DEVICE_TYPE:
                    self._device_type = i
                elif i in self.BROWSER_TYPE:
                    self._browser = i
                else:
                    raise ValueError('Unknown user agent description: {}'.format(i))
            if self._browser is None:
                self._browser = 'chrome'
            if self._device_type is None:
                self._device_type = 'desktop'
            ua = self._gen_user_agent(self._device_type, self._browser)
        if not ua:
            ua = 'xpaw/{}'.format(__version__)
        return ua

    @staticmethod
    def _gen_user_agent(device, browser):
        if browser == 'chrome':
            chrome_version = '{}.0.{}.{}'.format(random.randint(51, 70),
                                                 random.randint(0, 9999), random.randint(0, 99))
            webkit = '{}.{}'.format(random.randint(531, 600), random.randint(0, 99))
            if device == 'desktop':
                os = 'Macintosh; Intel Mac OS X 10_13_6'
                return ('Mozilla/5.0 ({}) AppleWebKit/{} (KHTML, like Gecko) '
                        'Chrome/{} Safari/{}').format(os, webkit, chrome_version, webkit)
            elif device == 'mobile':
                os = 'iPhone; CPU iPhone OS 11_4_1 like Mac OS X'
                mobile = '15E{:03d}'.format(random.randint(0, 999))
                return ('Mozilla/5.0 ({}) AppleWebKit/{} (KHTML, like Gecko) '
                        'CriOS/{} Mobile/{} Safari/{}').format(os, webkit, chrome_version, mobile, webkit)

    def _set_browser_default_headers(self, request):
        if self._browser in self.BROWSER_DEFAULT_HEADERS:
            for k, v in self.BROWSER_DEFAULT_HEADERS[self._browser].items():
                request.headers.setdefault(k, v)
