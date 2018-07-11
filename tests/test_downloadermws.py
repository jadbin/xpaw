# coding=utf-8

import re
import json

import pytest

from xpaw.config import Config
from xpaw.http import HttpRequest, HttpResponse
from xpaw.downloadermws import *
from xpaw.errors import IgnoreRequest, NetworkError, NotEnabled
from xpaw.version import __version__
from xpaw.downloader import Downloader
from xpaw.eventbus import EventBus


class Cluster:
    def __init__(self, loop=None, **kwargs):
        self.loop = loop
        self.config = Config(kwargs)
        self.event_bus = EventBus()


class TestImitatingProxyMiddleware:
    def test_handle_request(self):
        mw = ImitatingProxyMiddleware.from_cluster(Cluster(imitating_proxy_enabled=True))
        req = HttpRequest("http://example.com")
        mw.handle_request(req)
        assert re.search(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", req.headers["X-Forwarded-For"])
        assert req.headers['Via'] == '{} xpaw'.format(__version__)

    def test_not_enabled(self):
        with pytest.raises(NotEnabled):
            ImitatingProxyMiddleware.from_cluster(Cluster())


class TestDefaultHeadersMiddleware:
    def test_handle_request(self):
        default_headers = {"User-Agent": "xpaw", "Connection": "keep-alive"}
        req_headers = {"User-Agent": "xpaw-test", "Connection": "keep-alive"}
        mw = DefaultHeadersMiddleware.from_cluster(Cluster(default_headers=default_headers))
        req = HttpRequest("http://example.com", headers={"User-Agent": "xpaw-test"})
        mw.handle_request(req)
        assert req_headers == req.headers

    def test_not_enabled(self, loop):
        with pytest.raises(NotEnabled):
            DefaultHeadersMiddleware.from_cluster(Cluster(loop=loop, default_headers=None))


class Random:
    def __init__(self):
        self.iter = 0

    def choice(self, seq):
        res = seq[self.iter % len(seq)]
        self.iter += 1
        return res


class TestProxyMiddleware:
    def test_proxy_str(self, loop):
        proxy = '153.10.32.18:3128'
        mw = ProxyMiddleware.from_cluster(Cluster(proxy=proxy, loop=loop))
        req = HttpRequest(URL("http://example.com"))
        mw.handle_request(req)
        assert req.meta['proxy'] == '153.10.32.18:3128'

    def test_proxy_list(self, monkeypatch, loop):
        monkeypatch.setattr(random, 'choice', Random().choice)
        proxy_list = ["105.12.103.232:3128", "16.82.3.20:3128"]
        mw = ProxyMiddleware.from_cluster(Cluster(proxy=proxy_list, loop=loop))
        req = HttpRequest("http://example.com")
        for i in range(len(proxy_list)):
            mw.handle_request(req)
            assert req.meta['proxy'] == proxy_list[i]

        req2 = HttpRequest('ftp://example.com')
        mw.handle_request(req2)
        assert 'proxy' not in req2.meta

    def test_proxy_dict(self, monkeypatch, loop):
        monkeypatch.setattr(random, 'choice', Random().choice)
        proxy_dict = {'http': ['132.39.13.100:3128', '18.39.9.10:3128'], 'https': '177.13.233.2:3128'}
        mw = ProxyMiddleware.from_cluster(Cluster(proxy=proxy_dict, loop=loop))
        req_list = []
        for i in ['http://example.com', 'https://example.com', 'http://example.com', 'http://example.com']:
            req_list.append(HttpRequest(i))
        res = ['132.39.13.100:3128', '177.13.233.2:3128', '132.39.13.100:3128', '18.39.9.10:3128']
        for i in range(len(req_list)):
            mw.handle_request(req_list[i])
            assert req_list[i].meta['proxy'] == res[i]

    async def test_not_enabled(self, loop):
        with pytest.raises(NotEnabled):
            ProxyMiddleware.from_cluster(Cluster(loop=loop))


class TestRetryMiddleware:
    def test_handle_reponse(self):
        mw = RetryMiddleware.from_cluster(Cluster(retry_http_status=(500,)))
        req = HttpRequest("http://example.com")
        resp = HttpResponse(URL("http://example.com"), 502)
        assert mw.handle_response(req, resp) is None
        req2 = HttpRequest("http://example.com")
        resp2 = HttpResponse(URL("http://example.com"), 500)
        retry_req2 = mw.handle_response(req2, resp2)
        assert retry_req2.meta['retry_times'] == 1
        assert str(retry_req2.url) == str(req2.url)
        req3 = HttpRequest("http://example.com")
        resp3 = HttpResponse(URL("http://example.com"), 500)
        req3.meta['retry_times'] = 2
        retry_req3 = mw.handle_response(req3, resp3)
        assert retry_req3.meta['retry_times'] == 3
        assert str(retry_req3.url) == str(req3.url)
        req4 = HttpRequest("http://example.com")
        req4.meta['retry_times'] = 3
        resp4 = HttpResponse(URL("http://example.com"), 500)
        with pytest.raises(IgnoreRequest):
            mw.handle_response(req4, resp4)

    def test_handle_error(self):
        mw = RetryMiddleware.from_cluster(Cluster())
        req = HttpRequest("http://example.com")
        err = ValueError()
        assert mw.handle_error(req, err) is None
        err2 = NetworkError()
        retry_req2 = mw.handle_error(req, err2)
        assert isinstance(retry_req2, HttpRequest) and str(retry_req2.url) == str(req.url)

    def test_retry(self):
        max_retry_times = 2
        mw = RetryMiddleware.from_cluster(Cluster(max_retry_times=max_retry_times,
                                                  retry_http_status=(500,)))
        req = HttpRequest("http://example.com")
        for i in range(max_retry_times):
            retry_req = mw.retry(req, "")
            assert isinstance(retry_req, HttpRequest) and str(retry_req.url) == str(req.url)
            req = retry_req
        with pytest.raises(IgnoreRequest):
            mw.retry(req, "")

    def test_not_enabled(self):
        with pytest.raises(NotEnabled):
            RetryMiddleware.from_cluster(Cluster(retry_enabled=False))

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


class TestCookiesMiddleware:
    def test_not_enabled(self):
        with pytest.raises(NotEnabled):
            CookiesMiddleware.from_cluster(Cluster())

    async def test_cookie_jar(self, loop):
        mw = CookiesMiddleware.from_cluster(Cluster(cookie_jar_enabled=True, loop=loop))
        downloader = Downloader(timeout=60, loop=loop)
        seed = str(random.randint(0, 2147483647))
        req = HttpRequest("http://httpbin.org/cookies/set?seed={}".format(seed))
        mw.handle_request(req)
        await downloader.download(req)
        req2 = HttpRequest("http://httpbin.org/cookies")
        mw.handle_request(req2)
        resp = await downloader.download(req2)
        assert resp.status == 200
        cookies = json.loads(resp.text)["cookies"]
        assert len(cookies) == 1 and cookies.get("seed") == seed
        req3 = HttpRequest("http://httpbin.org/cookies/delete?seed=")
        mw.handle_request(req3)
        await downloader.download(req3)
        req4 = HttpRequest("http://httpbin.org/cookies")
        mw.handle_request(req4)
        resp = await downloader.download(req4)
        assert resp.status == 200
        cookies = json.loads(resp.text)["cookies"]
        assert len(cookies) == 0

    async def test_dump(self, loop, tmpdir):
        mw = CookiesMiddleware.from_cluster(Cluster(cookie_jar_enabled=True, loop=loop, dump_dir=str(tmpdir)))
        downloader = Downloader(timeout=60, loop=loop)
        seed = str(random.randint(0, 2147483647))
        req = HttpRequest("http://httpbin.org/cookies/set?seed={}".format(seed))
        mw.handle_request(req)
        await downloader.download(req)
        mw.close()
        mw2 = CookiesMiddleware.from_cluster(Cluster(cookie_jar_enabled=True, loop=loop, dump_dir=str(tmpdir)))
        mw2.open()
        req2 = HttpRequest("http://httpbin.org/cookies")
        mw2.handle_request(req2)
        resp = await downloader.download(req2)
        assert resp.status == 200
        cookies = json.loads(resp.text)["cookies"]
        assert len(cookies) == 1 and cookies.get("seed") == seed


class TestSpeedLimitMiddleware:
    async def test_value_error(self, loop):
        with pytest.raises(ValueError):
            SpeedLimitMiddleware.from_cluster(Cluster(speed_limit_enabled=True,
                                                      speed_limit_rate=0,
                                                      speed_limit_burst=1,
                                                      loop=loop))
        with pytest.raises(ValueError):
            SpeedLimitMiddleware.from_cluster(Cluster(speed_limit_enabled=True,
                                                      speed_limit_rate=1,
                                                      speed_limit_burst=0,
                                                      loop=loop))

    async def test_not_enabled(self, loop):
        with pytest.raises(NotEnabled):
            SpeedLimitMiddleware.from_cluster(Cluster(speed_limit_rate=1,
                                                      speed_limit_burst=1,
                                                      loop=loop))

    async def test_handle_request(self, loop):
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
        mw = SpeedLimitMiddleware.from_cluster(Cluster(speed_limit_enabled=True,
                                                       speed_limit_rate=1000,
                                                       speed_limit_burst=5,
                                                       loop=loop))
        futures = []
        for i in range(100):
            futures.append(asyncio.ensure_future(processor(), loop=loop))
        mw.open()
        await asyncio.sleep(0.1, loop=loop)
        mw.close()
        for f in futures:
            assert f.cancel() is True
        await asyncio.sleep(0.01, loop=loop)
        assert counter.n <= 105


class TestUserAgentMiddleware:
    def test_not_enabled(self):
        with pytest.raises(NotEnabled):
            UserAgentMiddleware.from_cluster(Cluster(user_agent=None))

    def test_static_user_agent(self):
        user_agent = 'test user agent'
        mw = UserAgentMiddleware.from_cluster(Cluster(user_agent=user_agent))
        req = HttpRequest('http://example.com')
        mw.handle_request(req)
        assert req.headers.get('User-Agent') == user_agent

    def test_gen_user_agent(self):
        mw = UserAgentMiddleware.from_cluster(Cluster(user_agent=':desktop,chrome'))
        req = HttpRequest('http://example.com')
        mw.handle_request(req)
        assert 'Chrome' in req.headers.get('User-Agent')

        mw2 = UserAgentMiddleware.from_cluster(Cluster(user_agent=':mobile,chrome'))
        req2 = HttpRequest('http://example.com')
        mw2.handle_request(req2)
        assert 'CriOS' in req2.headers.get('User-Agent') and 'Mobile' in req2.headers.get('User-Agent')

    def test_unknown_user_agent_description(self):
        with pytest.raises(ValueError):
            UserAgentMiddleware.from_cluster(Cluster(user_agent=':unknown'))

    def test_random_user_agent(self):
        mw = UserAgentMiddleware.from_cluster(Cluster(random_user_agent=True))
        req = HttpRequest('http://example.com')
        req2 = HttpRequest('http://example.com')
        mw.handle_request(req)
        mw.handle_request(req2)
        assert 'User-Agent' in req.headers
        assert req.headers.get('User-Agent') != req2.headers.get('User-Agent')
        assert 'Chrome' in req.headers.get('User-Agent')

    def test_random_user_agent2(self):
        mw = UserAgentMiddleware.from_cluster(Cluster(user_agent=':mobile', random_user_agent=True))
        for i in range(30):
            req = HttpRequest('http://example.com')
            mw.handle_request(req)
            assert 'User-Agent' in req.headers
            assert 'CriOS' in req.headers.get('User-Agent') and 'Mobile' in req.headers.get('User-Agent')
