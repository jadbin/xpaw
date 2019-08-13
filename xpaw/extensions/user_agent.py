# coding=utf-8

import re
import random
import logging

from xpaw import __version__

log = logging.getLogger(__name__)

__all__ = ['UserAgentMiddleware']


def copy_and_update(d, u):
    r = dict(d)
    r.update(u)
    return r


class UserAgentMiddleware:
    DEVICE_TYPE = {'desktop', 'mobile'}
    DESKTOP_DEFAULT_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36"
    }
    MOBILE_DEFAULT_HEADERS = copy_and_update(DESKTOP_DEFAULT_HEADERS, {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 8.0; Pixel 2 Build/OPD3.170816.012) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Mobile Safari/537.36'
    })

    chrome_version_split = re.compile(r'(Chrome/\d+\.\d+.\d+.\d+)')

    def __init__(self, user_agent=None, random_user_agent=False):
        self._device_type = None
        self._browser = None
        self._is_random = random_user_agent
        self._user_agent = self._make_user_agent(user_agent)

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
            user_agent = self._gen_user_agent()
        else:
            user_agent = self._user_agent
        request.headers['User-Agent'] = user_agent
        self._set_browser_default_headers(request)

    def _make_user_agent(self, ua):
        if ua and ua.startswith(':'):
            for i in ua[1:].split(','):
                if i in self.DEVICE_TYPE:
                    self._device_type = i
                else:
                    log.warning('Unknown user agent descriptor: {}'.format(i))
            if self._device_type is None:
                self._device_type = 'desktop'
            ua = self._gen_user_agent()
        if not ua:
            ua = 'xpaw/{}'.format(__version__)
        return ua

    def _gen_user_agent(self):
        ua = None
        if self._device_type == 'desktop':
            ua = self.DESKTOP_DEFAULT_HEADERS['User-Agent']
        elif self._device_type == 'mobile':
            ua = self.MOBILE_DEFAULT_HEADERS['User-Agent']
        if self._is_random:
            s = self.chrome_version_split.split(ua)
            if len(s) == 3:
                v = s[1].split('.')
                for i in range(1, len(v)):
                    x = int(v[i])
                    if x > 0:
                        x = random.randint(0, x)
                        v[i] = str(x)
                s[1] = '.'.join(v)
                ua = ''.join(s)
        return ua

    def _set_browser_default_headers(self, request):
        headers = {}
        if self._device_type == 'desktop':
            headers = self.DESKTOP_DEFAULT_HEADERS
        elif self._device_type == 'mobile':
            headers = self.MOBILE_DEFAULT_HEADERS
        for k, v in headers.items():
            request.headers.setdefault(k, v)
