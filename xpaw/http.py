# coding=utf-8

import inspect


class HttpRequest:
    def __init__(self, url, method="GET",
                 body=None, headers=None, cookies=None, proxy=None,
                 meta=None, callback=None):
        """
        Construct an HTTP request.
        """
        self.url = url
        self.method = method
        self.body = body
        self.headers = headers or {}
        self.cookies = cookies or {}
        self.proxy = proxy
        self._meta = dict(meta) if meta else {}
        if callback and inspect.ismethod(callback):
            callback = callback.__name__
        self.callback = callback

    @property
    def meta(self):
        return self._meta

    def copy(self):
        kw = {}
        for x in ["url", "method", "body", "headers", "cookies", "proxy", "meta", "callback"]:
            kw.setdefault(x, getattr(self, x))
        return HttpRequest(**kw)


class HttpResponse:
    def __init__(self, url, status,
                 body=None, headers=None, cookies=None,
                 request=None):
        """
        Construct an HTTP response.
        """
        self.url = url
        self.status = status
        self.body = body
        self.headers = headers
        self.cookies = cookies
        self.request = request

    @property
    def meta(self):
        if self.request:
            return self.request.meta
        return None

    def copy(self):
        kw = {}
        for x in ["url", "status", "body", "headers", "cookies", "request"]:
            kw.setdefault(x, getattr(self, x))
        return HttpResponse(**kw)
