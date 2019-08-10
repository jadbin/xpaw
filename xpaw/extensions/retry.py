# coding=utf-8

import logging

from xpaw.errors import ClientError, NotEnabled, HttpError
from xpaw.utils import with_not_none_params

log = logging.getLogger(__name__)

__all__ = ['RetryMiddleware']


class RetryMiddleware:
    RETRY_ERRORS = (ClientError,)
    RETRY_HTTP_STATUS = (500, 502, 503, 504, 408, 429)

    def __init__(self, max_retry_times=3, retry_http_status=None):
        self._max_retry_times = max_retry_times
        self._retry_http_status = retry_http_status or self.RETRY_HTTP_STATUS

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{}(max_retry_times={}, retry_http_status={})' \
            .format(cls_name, repr(self._max_retry_times), repr(self._retry_http_status))

    @classmethod
    def from_crawler(cls, crawler):
        config = crawler.config
        if not config.getbool('retry_enabled'):
            raise NotEnabled
        return cls(**with_not_none_params(max_retry_times=config.getint('max_retry_times'),
                                          retry_http_status=config.getlist('retry_http_status')))

    def handle_response(self, request, response):
        for p in self._retry_http_status:
            if self.match_status(p, response.status):
                return self.retry(request, "HTTP status={}".format(response.status))

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
            for i in range(n):
                if pattern[i] != "x" and pattern[i] != "X" and pattern[i] != s[i]:
                    match = False
                    break
        if verse:
            match = not match
        return match

    def handle_error(self, request, error):
        if isinstance(error, self.RETRY_ERRORS):
            return self.retry(request, error)
        if isinstance(error, HttpError):
            for p in self._retry_http_status:
                if self.match_status(p, error.response.status):
                    return self.retry(request, "HTTP status={}".format(error.response.status))

    def retry(self, request, reason):
        retry_times = request.meta.get('retry_times', 0) + 1
        if retry_times <= self._max_retry_times:
            log.debug('Retry %s (failed %s times): %s', request, retry_times, reason)
            retry_req = request.copy()
            retry_req.meta['retry_times'] = retry_times
            retry_req.dont_filter = True
            return retry_req
        else:
            log.debug('Give up retrying %s (failed %s times): %s', request, retry_times, reason)
