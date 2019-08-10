# coding=utf-8

import random
import logging

from xpaw import __version__

log = logging.getLogger(__name__)

__all__ = ['UserAgentMiddleware']


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
