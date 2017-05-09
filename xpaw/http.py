# coding=utf-8

import inspect

from xpaw.utils.web import get_encoding_from_header, get_encoding_from_content


class HttpRequest:
    def __init__(self, url, method="GET", body=None,
                 headers=None, cookies=None, proxy=None,
                 meta=None, callback=None, errback=None):
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
        if errback and inspect.ismethod(errback):
            errback = errback.__name__
        self.errback = errback

    @property
    def meta(self):
        return self._meta

    def copy(self):
        kw = {}
        for x in ["url", "method", "body", "headers", "cookies", "proxy", "meta", "callback", "errback"]:
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
    def encoding(self):
        if hasattr(self, "_encoding"):
            return self._encoding
        encoding = get_encoding_from_header(self.headers.get("content-type"))
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
        encoding = self.encoding
        content = ""
        try:
            content = self.body.decode(encoding, errors="replace")
        except LookupError:
            content = self.body.decode(encoding, errors="replace")
        self._text = content
        return self._text

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
