# coding=utf-8

import re
import logging

from xpaw.config import BaseConfig
from xpaw.errors import ResponseNotMatch, IgnoreRequest, NetworkError

log = logging.getLogger(__name__)


class RetryMiddleware:
    RETRY_ERRORS = (NetworkError, ResponseNotMatch)
    RETRY_HTTP_STATUS = (500, 502, 503, 504, 408)

    def __init__(self, max_retry_times, http_status):
        self._max_retry_times = max_retry_times
        self._http_status = http_status

    @classmethod
    def from_config(cls, config):
        c = config.get("retry")
        if c is None:
            c = {}
        c = BaseConfig(c)
        return cls(c.getint("max_retry_times", 3),
                   c.getlist("http_status", cls.RETRY_HTTP_STATUS))

    async def handle_response(self, request, response):
        for p in self._http_status:
            if self.match_status(p, response.status):
                return self.retry(request, "http status={}".format(response.status))

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
            i = 0
            while i < n:
                if pattern[i] != "x" and pattern[i] != "X" and pattern[i] != s[i]:
                    match = False
                    break
                i += 1
        if verse:
            match = not match
        return match

    async def handle_error(self, request, error):
        if isinstance(error, self.RETRY_ERRORS):
            return self.retry(request, "{}: {}".format(type(error), error))

    def retry(self, request, reason):
        retry_times = request.meta.get("_retry_times", 0) + 1
        if retry_times <= self._max_retry_times:
            log.debug("We will retry the request(url={}) because of {}".format(request.url, reason))
            request.meta["_retry_times"] = retry_times
            return request.copy()
        else:
            raise IgnoreRequest("The request(url={}) has been retried {} times,"
                                " and it will be aborted.".format(request.url, self._max_retry_times))


class ResponseMatchMiddleware:
    def __init__(self, patterns):
        self._patterns = patterns

    @classmethod
    def from_config(cls, config):
        c = config.getlist("response_match")
        return cls([_ResponseMatchPattern(i.get("url_pattern"),
                                          i.get("body_pattern"),
                                          i.get("encoding"))
                    for i in c])

    async def handle_response(self, request, response):
        for p in self._patterns:
            if p.not_match(request, response):
                raise ResponseNotMatch("Response body does not fit the pattern")


class _ResponseMatchPattern:
    def __init__(self, url_pattern, body_pattern, encoding):
        if not url_pattern:
            raise ValueError("url pattern is none")
        if not body_pattern:
            raise ValueError("body pattern is none")
        self._url_pattern = re.compile(url_pattern)
        self._body_pattern = re.compile(body_pattern)
        self._encoding = encoding

    def not_match(self, request, response):
        req_url = str(request.url)
        if response.body:
            if self._url_pattern.search(req_url):
                if self._encoding:
                    text = response.body.decode(self._encoding, errors="replace")
                else:
                    text = response.text
                if not self._body_pattern.search(text):
                    return True
        return False
