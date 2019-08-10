# coding=utf-8

import inspect

from tornado.httputil import HTTPHeaders as _HttpHeaders

from .utils import get_encoding_from_content, get_encoding_from_content_type, make_url

HttpHeaders = _HttpHeaders


class HttpRequest:
    def __init__(self, url, method="GET", body=None, params=None, headers=None, proxy=None,
                 timeout=20, verify_ssl=False, allow_redirects=True, auth=None, proxy_auth=None,
                 priority=None, dont_filter=False, callback=None, errback=None, meta=None,
                 render=None):
        """
        Construct an HTTP request.
        """
        self.url = make_url(url, params)
        self.method = method
        self.body = body
        self.headers = headers
        self.proxy = proxy
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.allow_redirects = allow_redirects
        self.auth = auth
        self.proxy_auth = proxy_auth
        self.priority = priority
        self.dont_filter = dont_filter
        self.callback = callback
        self.errback = errback
        self._meta = dict(meta) if meta else {}
        self.render = render

    def __str__(self):
        return '<{}, {}>'.format(self.method, self.url)

    __repr__ = __str__

    @property
    def meta(self):
        return self._meta

    def copy(self):
        return self.replace()

    def replace(self, **kwargs):
        for i in ["url", "method", "body", "headers", "proxy",
                  "timeout", "verify_ssl", "allow_redirects", "auth", "proxy_auth",
                  "priority", "dont_filter", "callback", "errback", "meta",
                  "render"]:
            kwargs.setdefault(i, getattr(self, i))
        return type(self)(**kwargs)

    def to_dict(self):
        callback = self.callback
        if inspect.ismethod(callback):
            callback = callback.__name__
        errback = self.errback
        if inspect.ismethod(errback):
            errback = errback.__name__
        d = {
            'url': self.url,
            'method': self.method,
            'body': self.body,
            'headers': self.headers,
            'proxy': self.proxy,
            'timeout': self.timeout,
            'verify_ssl': self.verify_ssl,
            'allow_redirects': self.allow_redirects,
            'auth': self.auth,
            'proxy_auth': self.proxy_auth,
            'priority': self.priority,
            'dont_filter': self.dont_filter,
            'callback': callback,
            'errback': errback,
            'meta': self.meta,
            'render': self.render
        }
        return d

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


class HttpResponse:
    def __init__(self, url, status, body=None, headers=None,
                 request=None, encoding=None):
        """
        Construct an HTTP response.
        """
        self.url = url
        self.status = status
        self.body = body
        self.headers = headers
        self.request = request
        self._encoding = encoding

    def __str__(self):
        return '<{}, {}>'.format(self.status, self.url)

    __repr__ = __str__

    @property
    def encoding(self):
        if self._encoding:
            return self._encoding
        encoding = get_encoding_from_content_type(self.headers.get("Content-Type"))
        if not encoding and self.body:
            encoding = get_encoding_from_content(self.body)
        return encoding or 'utf-8'

    @encoding.setter
    def encoding(self, value):
        self._encoding = value

    @property
    def text(self):
        if hasattr(self, "_text") and self._text:
            return self._text
        if not self.body:
            return ""
        if isinstance(self.body, bytes):
            self._text = self.body.decode(self.encoding, errors="replace")
        else:
            self._text = self.body
        return self._text

    @property
    def meta(self):
        if self.request:
            return self.request.meta

    def copy(self):
        return self.replace()

    def replace(self, **kwargs):
        for i in ["url", "status", "body", "headers", "request"]:
            kwargs.setdefault(i, getattr(self, i))
        return type(self)(**kwargs)
