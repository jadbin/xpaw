# coding=utf-8

import inspect

from .utils import get_encoding_from_header, get_encoding_from_content


class HttpRequest:
    def __init__(self, url, method="GET", body=None, params=None,
                 auth=None, headers=None, cookies=None, proxy=None, proxy_auth=None,
                 meta=None, priority=None, dont_filter=False, callback=None, errback=None):
        """
        Construct an HTTP request.
        """
        self.url = url
        self.method = method
        self.body = body
        self.params = params
        self.auth = auth
        self.headers = headers or {}
        self.cookies = cookies or {}
        self.proxy = proxy
        self.proxy_auth = proxy_auth
        self._meta = dict(meta) if meta else {}
        self.priority = priority
        self.dont_filter = dont_filter
        if callback and inspect.ismethod(callback):
            callback = callback.__name__
        self.callback = callback
        if errback and inspect.ismethod(errback):
            errback = errback.__name__
        self.errback = errback

    @property
    def meta(self):
        return self._meta

    def copy(self):
        return self.new()

    def new(self, **kwargs):
        for i in ["url", "method", "body", "params", "auth", "headers", "cookies", "proxy", "proxy_auth",
                  "meta", "priority", "dont_filter", "callback", "errback"]:
            kwargs.setdefault(i, getattr(self, i))
        return type(self)(**kwargs)


class HttpResponse:
    def __init__(self, url, status, body=None, headers=None, cookies=None,
                 request=None):
        """
        Construct an HTTP response.
        """
        self.url = url
        self.status = int(status)
        self.body = body
        self.headers = headers or {}
        self.cookies = cookies or {}
        self.request = request

    @property
    def encoding(self):
        if hasattr(self, "_encoding"):
            return self._encoding
        encoding = get_encoding_from_header(self.headers.get("Content-Type"))
        if not encoding and self.body:
            encoding = get_encoding_from_content(self.body)
        self._encoding = encoding or "utf-8"
        return self._encoding

    @encoding.setter
    def encoding(self, value):
        self._encoding = value

    @property
    def text(self):
        if hasattr(self, "_text") and self._text:
            return self._text
        if not self.body:
            return ""
        self._text = self.body.decode(self.encoding, errors="replace")
        return self._text

    @property
    def meta(self):
        if self.request:
            return self.request.meta
        return None

    def copy(self):
        return self.new()

    def new(self, **kwargs):
        for i in ["url", "status", "body", "headers", "cookies", "request"]:
            kwargs.setdefault(i, getattr(self, i))
        return type(self)(**kwargs)
