# coding=utf-8

import pytest

from xpaw.http import HttpRequest, HttpResponse
from xpaw.downloader_middlewares import *
from xpaw.errors import ClientError, NotEnabled
from .crawler import Crawler


class TestDefaultHeadersMiddleware:
    def test_handle_request(self):
        default_headers = {"User-Agent": "xpaw", "Connection": "keep-alive"}
        mw = DefaultHeadersMiddleware.from_crawler(Crawler(default_headers=default_headers))
        req = HttpRequest("http://example.com", headers={"Connection": "close"})
        mw.handle_request(req)
        assert req.headers == {"User-Agent": "xpaw", "Connection": "close"}

    def test_not_enabled(self):
        with pytest.raises(NotEnabled):
            DefaultHeadersMiddleware.from_crawler(Crawler(default_headers=None))


class Random:
    def __init__(self):
        self.iter = 0

    def choice(self, seq):
        res = seq[self.iter % len(seq)]
        self.iter += 1
        return res


class TestProxyMiddleware:
    def test_proxy_str(self):
        proxy = '127.0.0.1:3128'
        mw = ProxyMiddleware.from_crawler(Crawler(proxy=proxy))
        req = HttpRequest("http://example.com")
        mw.handle_request(req)
        assert req.proxy == proxy

    def test_proxy_dict(self):
        proxy_dict = {'http': '127.0.0.1:3128', 'https': '127.0.0.1:3129'}
        mw = ProxyMiddleware.from_crawler(Crawler(proxy=proxy_dict))
        req_list = []
        for i in ['http://example.com', 'https://example.com']:
            req_list.append(HttpRequest(i))
        res = ['127.0.0.1:3128', '127.0.0.1:3129']
        for i in range(len(req_list)):
            mw.handle_request(req_list[i])
            assert req_list[i].proxy == res[i]

    @pytest.mark.asyncio
    async def test_not_enabled(self):
        with pytest.raises(NotEnabled):
            ProxyMiddleware.from_crawler(Crawler())


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


class TestSpeedLimitMiddleware:
    @pytest.mark.asyncio
    async def test_value_error(self):
        with pytest.raises(ValueError):
            SpeedLimitMiddleware.from_crawler(Crawler(speed_limit={'rate': 0, 'burst': 1}))
        with pytest.raises(ValueError):
            SpeedLimitMiddleware.from_crawler(Crawler(speed_limit={'rate': 1, 'burst': 0}))

    @pytest.mark.asyncio
    async def test_not_enabled(self):
        with pytest.raises(NotEnabled):
            SpeedLimitMiddleware.from_crawler(Crawler())

    @pytest.mark.asyncio
    async def test_handle_request(self):
        class Counter:
            def __init__(self):
                self.n = 0

            def inc(self):
                self.n += 1

        async def processor():
            while True:
                await mw.handle_request(None)
                counter.inc()

        counter = Counter()
        mw = SpeedLimitMiddleware.from_crawler(Crawler(speed_limit={'rate': 1000, 'burst': 5}))
        futures = []
        for i in range(100):
            futures.append(asyncio.ensure_future(processor()))
        mw.open()
        await asyncio.sleep(0.1)
        mw.close()
        for f in futures:
            assert f.cancel() is True
        await asyncio.sleep(0.01)
        assert counter.n <= 105


class TestUserAgentMiddleware:
    def test_static_user_agent(self):
        user_agent = 'test user agent'
        mw = UserAgentMiddleware.from_crawler(Crawler(user_agent=user_agent))
        req = HttpRequest('http://example.com', headers={})
        mw.handle_request(req)
        assert req.headers.get('User-Agent') == user_agent

    def test_gen_user_agent(self):
        mw = UserAgentMiddleware.from_crawler(Crawler(user_agent=':desktop,chrome'))
        req = HttpRequest('http://example.com', headers={})
        mw.handle_request(req)
        assert 'Chrome' in req.headers.get('User-Agent')

        mw2 = UserAgentMiddleware.from_crawler(Crawler(user_agent=':mobile,chrome'))
        req2 = HttpRequest('http://example.com', headers={})
        mw2.handle_request(req2)
        assert 'CriOS' in req2.headers.get('User-Agent') and 'Mobile' in req2.headers.get('User-Agent')

    def test_unknown_user_agent_description(self):
        with pytest.raises(ValueError):
            UserAgentMiddleware.from_crawler(Crawler(user_agent=':unknown'))

    def test_random_user_agent(self):
        mw = UserAgentMiddleware.from_crawler(Crawler(random_user_agent=True))
        req = HttpRequest('http://example.com', headers={})
        req2 = HttpRequest('http://example.com', headers={})
        mw.handle_request(req)
        mw.handle_request(req2)
        assert 'User-Agent' in req.headers
        assert req.headers.get('User-Agent') != req2.headers.get('User-Agent')
        assert 'Chrome' in req.headers.get('User-Agent')

    def test_random_user_agent2(self):
        mw = UserAgentMiddleware.from_crawler(Crawler(user_agent=':mobile', random_user_agent=True))
        for i in range(30):
            req = HttpRequest('http://example.com', headers={})
            mw.handle_request(req)
            assert 'User-Agent' in req.headers
            assert 'CriOS' in req.headers.get('User-Agent') and 'Mobile' in req.headers.get('User-Agent')
