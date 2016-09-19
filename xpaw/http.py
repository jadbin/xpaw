# coding=utf-8


class HttpRequest:
    def __init__(self, url, method="GET", *, proxy=None, headers=None, body=None, cookies=None, meta=None):
        """
        Construct an HTTP request.

        :param str url: URL
        :param str method: HTTP method
        :param str proxy: HTTP proxy address
        :param dict headers: HTTP headers
        :param bytes body: HTTP body
        :param dict cookies: HTTP cookies
        :param dict meta: meta data
        """
        self.url = url
        self.method = method
        self.proxy = proxy
        self.headers = headers or {}
        self.body = body
        self.cookies = cookies or {}
        self._meta = dict(meta) if meta else {}

    @property
    def meta(self):
        return self._meta

    def copy(self):
        kw = {}
        for x in ["url", "method", "proxy", "headers", "body", "cookies", "meta"]:
            kw.setdefault(x, getattr(self, x))
        return HttpRequest(**kw)


class HttpResponse:
    def __init__(self, url, status, *, headers=None, body=None, cookies=None, request=None):
        """
        Construct an HTTP response.

        :param str url: URL
        :param int status: HTTP status
        :param dict headers: HTTP headers
        :param bytes body: HTTP body
        :param cookies: HTTP cookies
        :param xpaw.http.HttpRequest request: the corresponding HTTP request
        """
        self.url = url
        self.status = status
        self.headers = headers
        self.body = body
        self.cookies = cookies
        self.request = request

    @property
    def meta(self):
        if self.request:
            return self.request.meta
        return None

    def copy(self):
        kw = {}
        for x in ["url", "status", "headers", "body", "cookies", "request"]:
            kw.setdefault(x, getattr(self, x))
        return HttpResponse(**kw)
