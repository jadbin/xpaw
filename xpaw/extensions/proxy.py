# coding=utf-8

import logging
from urllib.parse import urlsplit

from xpaw.errors import NotEnabled

log = logging.getLogger(__name__)

__all__ = ['ProxyMiddleware']


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
