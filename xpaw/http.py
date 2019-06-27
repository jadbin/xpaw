# coding=utf-8

from urllib.parse import urlsplit, parse_qs

from tornado.httputil import HTTPHeaders

from .utils import get_encoding_from_content, get_encoding_from_content_type, make_url

HttpHeaders = HTTPHeaders


class HttpRequest:
    def __init__(self, url, method="GET", body=None, params=None, headers=None, proxy=None,
                 timeout=20, verify_ssl=False, allow_redirects=True, auth=None, proxy_auth=None,
                 priority=None, dont_filter=False, callback=None, errback=None, meta=None,
                 render=False, on_ready=None):
        """
        Construct an HTTP request.
        """
        self.url = make_url(url, params=params)
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
        self.on_ready = on_ready

    def __str__(self):
        return '<{}, {}>'.format(self.method, self.url)

    __repr__ = __str__

    @property
    def params(self):
        return parse_qs(urlsplit(self.url).query)

    @property
    def meta(self):
        return self._meta

    def copy(self):
        return self.replace()

    def replace(self, **kwargs):
        for i in ["url", "method", "body", "headers", "proxy",
                  "timeout", "verify_ssl", "allow_redirects", "auth", "proxy_auth",
                  "priority", "dont_filter", "callback", "errback", "meta"]:
            kwargs.setdefault(i, getattr(self, i))
        return type(self)(**kwargs)


class HttpResponse:
    def __init__(self, url, status, body=None, headers=None,
                 request=None):
        """
        Construct an HTTP response.
        """
        self.url = url
        self.status = status
        self.body = body
        self.headers = headers
        self.request = request

    def __str__(self):
        return '<{}, {}>'.format(self.status, self.url)

    __repr__ = __str__

    @property
    def encoding(self):
        if hasattr(self, "_encoding"):
            return self._encoding
        encoding = get_encoding_from_content_type(self.headers.get("Content-Type"))
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

    def copy(self):
        return self.replace()

    def replace(self, **kwargs):
        for i in ["url", "status", "body", "headers", "request"]:
            kwargs.setdefault(i, getattr(self, i))
        return type(self)(**kwargs)
