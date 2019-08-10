# coding=utf-8


import pytest

from xpaw.http import HttpRequest, HttpResponse
from xpaw.extensions import RetryMiddleware
from xpaw.errors import ClientError, NotEnabled

from ..crawler import Crawler


class TestRetryMiddleware:
    def test_handle_reponse(self):
        mw = RetryMiddleware.from_crawler(Crawler(retry_http_status=(500,), max_retry_times=3))
        req = HttpRequest("http://example.com")
        resp = HttpResponse("http://example.com", 502)
        assert mw.handle_response(req, resp) is None
        req2 = HttpRequest("http://example.com")
        resp2 = HttpResponse("http://example.com", 500)
        retry_req2 = mw.handle_response(req2, resp2)
        assert retry_req2.meta['retry_times'] == 1
        assert str(retry_req2.url) == str(req2.url)
        req3 = HttpRequest("http://example.com")
        resp3 = HttpResponse("http://example.com", 500)
        req3.meta['retry_times'] = 2
        retry_req3 = mw.handle_response(req3, resp3)
        assert retry_req3.meta['retry_times'] == 3
        assert str(retry_req3.url) == str(req3.url)
        req4 = HttpRequest("http://example.com")
        req4.meta['retry_times'] = 3
        resp4 = HttpResponse("http://example.com", 500)
        assert mw.handle_response(req4, resp4) is None

    def test_handle_error(self):
        mw = RetryMiddleware.from_crawler(Crawler())
        req = HttpRequest("http://example.com")
        err = ValueError()
        assert mw.handle_error(req, err) is None
        for err in [ClientError()]:
            retry_req = mw.handle_error(req, err)
            assert isinstance(retry_req, HttpRequest) and str(retry_req.url) == str(req.url)

    def test_retry(self):
        max_retry_times = 2
        mw = RetryMiddleware.from_crawler(Crawler(max_retry_times=max_retry_times,
                                                  retry_http_status=(500,)))
        req = HttpRequest("http://example.com")
        for i in range(max_retry_times):
            retry_req = mw.retry(req, "")
            assert isinstance(retry_req, HttpRequest) and str(retry_req.url) == str(req.url)
            req = retry_req
        assert mw.retry(req, "") is None

    def test_not_enabled(self):
        with pytest.raises(NotEnabled):
            RetryMiddleware.from_crawler(Crawler(retry_enabled=False))

    def test_match_status(self):
        assert RetryMiddleware.match_status("200", 200) is True
        assert RetryMiddleware.match_status(200, 200) is True
        assert RetryMiddleware.match_status("2xX", 201) is True
        assert RetryMiddleware.match_status("40x", 403) is True
        assert RetryMiddleware.match_status("40X", 403) is True
        assert RetryMiddleware.match_status("50x", 403) is False
        assert RetryMiddleware.match_status("~20X", 200) is False
        assert RetryMiddleware.match_status("!20x", 400) is True
        assert RetryMiddleware.match_status("0200", 200) is False
