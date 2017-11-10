# coding=utf-8

import re
import pytest
from aiohttp import web

from xpaw.config import Config
from xpaw.http import HttpRequest, HttpResponse
from xpaw.downloadermws import *
from xpaw.errors import IgnoreRequest, NetworkError, NotEnabled


class Cluster:
    def __init__(self, loop=None, **kwargs):
        self.loop = loop
        self.config = Config(kwargs)


class TestImitatingProxyMiddleware:
    def test_handle_request(self):
        mw = ImitatingProxyMiddleware.from_cluster(Cluster(imitating_proxy_enabled=True))
        req = HttpRequest("http://httpbin.org")
        mw.handle_request(req)
        assert re.search(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", req.headers["X-Forwarded-For"])
        assert req.headers['Via'] == '1.1 xpaw'

    def test_not_enabled(self):
        with pytest.raises(NotEnabled):
            ImitatingProxyMiddleware.from_cluster(Cluster())


class TestDefaultHeadersMiddleware:
    def test_handle_request(self):
        default_headers = {"User-Agent": "xpaw", "Connection": "keep-alive"}
        req_headers = {"User-Agent": "xpaw-test", "Connection": "keep-alive"}
        mw = DefaultHeadersMiddleware.from_cluster(Cluster(default_headers=default_headers))
        req = HttpRequest("http://httpbin.org", headers={"User-Agent": "xpaw-test"})
        mw.handle_request(req)
        assert req_headers == req.headers

    def test_not_enabled(self, loop):
        with pytest.raises(NotEnabled):
            DefaultHeadersMiddleware.from_cluster(Cluster(loop=loop, default_headers=None))


def make_proxy_list():
    return ["127.0.0.1:3128", "127.0.0.2:3128"]


def make_another_proxy_list():
    return ["127.0.0.1:8080", "127.0.0.2:8080"]


def make_detail_proxy_list():
    return [{'addr': '127.0.0.1:3128'},
            {'addr': '127.0.0.2:3128', 'scheme': 'http'},
            {'addr': '127.0.0.3:3128', 'scheme': 'https', 'auth': 'root:123456'},
            {'addr': '127.0.0.4:3128', 'scheme': 'http,https'}]


async def make_proxy_agent(test_server):
    def get_proxies(request):
        return web.Response(body=json.dumps(server.proxy_list).encode("utf-8"),
                            charset="utf-8",
                            content_type="application/json")

    app = web.Application()
    app.router.add_route("GET", "/", get_proxies)
    server = await test_server(app)
    server.proxy_list = make_proxy_list()
    return server


class Random:
    def __init__(self):
        self.iter = 0

    def choice(self, seq):
        res = seq[self.iter % len(seq)]
        self.iter += 1
        return res


class TestProxyMiddleware:
    async def test_handle_request(self, monkeypatch, loop):
        monkeypatch.setattr(random, 'choice', Random().choice)
        proxy_list = make_proxy_list()
        mw = ProxyMiddleware.from_cluster(Cluster(proxy=proxy_list, loop=loop))
        target_list = proxy_list * 2
        req = HttpRequest("http://httpbin.org")
        for i in range(len(target_list)):
            await mw.handle_request(req)
            assert req.proxy == target_list[i]

        req2 = HttpRequest('ftp://httpbin.org')
        await mw.handle_request(req2)
        assert req2.proxy is None

    async def test_handle_request2(self, monkeypatch, loop):
        monkeypatch.setattr(random, 'choice', Random().choice)
        proxy_list = make_detail_proxy_list()
        mw = ProxyMiddleware.from_cluster(Cluster(proxy=proxy_list, loop=loop))
        reqs = [HttpRequest('http://httpbin.org'),
                HttpRequest('https://httpbin.org'),
                HttpRequest('https://httpbin.org'),
                HttpRequest('https://httpbin.org'),
                HttpRequest('http://httpbin.org'),
                HttpRequest('http://httpbin.org')]
        target_list = ['127.0.0.1:3128', '127.0.0.3:3128', '127.0.0.4:3128',
                       '127.0.0.1:3128', '127.0.0.2:3128', '127.0.0.4:3128']
        for i in range(len(reqs)):
            await mw.handle_request(reqs[i])
            assert reqs[i].proxy == target_list[i]

    async def test_handle_request_with_agent(self, monkeypatch, test_server, loop):
        monkeypatch.setattr(random, 'choice', Random().choice)
        server = await make_proxy_agent(test_server)
        mw = ProxyMiddleware.from_cluster(
            Cluster(proxy_agent="http://{}:{}".format(server.host, server.port),
                    loop=loop))
        mw.open()
        req = HttpRequest("http://httpbin.org")
        target_list = make_proxy_list() * 2
        for i in range(len(target_list)):
            await mw.handle_request(req)
            assert req.proxy == target_list[i]

        req2 = HttpRequest('ftp://httpbin.org')
        await mw.handle_request(req2)
        assert req2.proxy is None
        mw.close()

    async def test_handle_request_with_agent2(self, monkeypatch, test_server, loop):
        monkeypatch.setattr(random, 'choice', Random().choice)
        server = await make_proxy_agent(test_server)
        server.proxy_list = make_detail_proxy_list()
        mw = ProxyMiddleware.from_cluster(
            Cluster(proxy_agent="http://{}:{}".format(server.host, server.port),
                    loop=loop))
        mw.open()
        reqs = [HttpRequest('http://httpbin.org'),
                HttpRequest('https://httpbin.org'),
                HttpRequest('https://httpbin.org'),
                HttpRequest('https://httpbin.org'),
                HttpRequest('http://httpbin.org'),
                HttpRequest('http://httpbin.org')]
        target_list = ['127.0.0.1:3128', '127.0.0.3:3128', '127.0.0.4:3128',
                       '127.0.0.1:3128', '127.0.0.2:3128', '127.0.0.4:3128']
        for i in range(len(reqs)):
            await mw.handle_request(reqs[i])
            assert reqs[i].proxy == target_list[i]
        mw.close()

    async def test_update_proxy_list(self, monkeypatch, test_server, loop):
        monkeypatch.setattr(random, 'choice', Random().choice)
        server = await make_proxy_agent(test_server)
        mw = ProxyMiddleware.from_cluster(
            Cluster(proxy_agent="http://{}:{}".format(server.host, server.port),
                    loop=loop))
        monkeypatch.setattr(ProxyMiddleware, 'UPDATE_INTERVAL', 0.05)
        mw.open()
        await asyncio.sleep(0.1, loop=loop)
        req = HttpRequest("http://httpbin.org")
        target_list = make_proxy_list() * 2
        for i in range(len(target_list)):
            await mw.handle_request(req)
            assert req.proxy == target_list[i]
        server.proxy_list = make_another_proxy_list()
        await asyncio.sleep(0.1, loop=loop)
        target_list = make_another_proxy_list() * 2
        for i in range(len(target_list)):
            await mw.handle_request(req)
            assert req.proxy == target_list[i]
        mw.close()

    async def test_not_enabled(self, loop):
        with pytest.raises(NotEnabled):
            ProxyMiddleware.from_cluster(Cluster(loop=loop))


class TestRetryMiddleware:
    def test_handle_reponse(self):
        mw = RetryMiddleware.from_cluster(Cluster(retry_http_status=(500,)))
        req = HttpRequest("http://httpbin.org")
        resp = HttpResponse(URL("http://httpbin.org"), 502)
        assert mw.handle_response(req, resp) is None
        req2 = HttpRequest("http://httpbin.org")
        resp2 = HttpResponse(URL("http://httpbin.org"), 500)
        retry_req2 = mw.handle_response(req2, resp2)
        assert retry_req2.meta['retry_times'] == 1
        assert str(retry_req2.url) == str(req2.url)
        req3 = HttpRequest("http://httpbin.org")
        resp3 = HttpResponse(URL("http://httpbin.org"), 500)
        req3.meta['retry_times'] = 2
        retry_req3 = mw.handle_response(req3, resp3)
        assert retry_req3.meta['retry_times'] == 3
        assert str(retry_req3.url) == str(req3.url)
        req4 = HttpRequest("http://httpbin.org")
        req4.meta['retry_times'] = 3
        resp4 = HttpResponse(URL("http://httpbin.org"), 500)
        with pytest.raises(IgnoreRequest):
            mw.handle_response(req4, resp4)

    def test_handle_error(self):
        mw = RetryMiddleware.from_cluster(Cluster())
        req = HttpRequest("http://httpbin.org")
        err = ValueError()
        assert mw.handle_error(req, err) is None
        err2 = NetworkError()
        retry_req2 = mw.handle_error(req, err2)
        assert isinstance(retry_req2, HttpRequest) and str(retry_req2.url) == str(req.url)

    def test_retry(self):
        max_retry_times = 2
        mw = RetryMiddleware.from_cluster(Cluster(max_retry_times=max_retry_times,
                                                  retry_http_status=(500,)))
        req = HttpRequest("http://httpbin.org")
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


class TestSpeedLimitMiddleware:
    async def test_value_error(self, loop):
        with pytest.raises(ValueError):
            SpeedLimitMiddleware.from_cluster(Cluster(speed_limit_rate=0,
                                                      speed_limit_burst=1,
                                                      loop=loop))
        with pytest.raises(ValueError):
            SpeedLimitMiddleware.from_cluster(Cluster(speed_limit_rate=1,
                                                      speed_limit_burst=0,
                                                      loop=loop))

    async def test_not_enabled(self, loop):
        with pytest.raises(NotEnabled):
            SpeedLimitMiddleware.from_cluster(Cluster(speed_limit_burst=1,
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
        req = HttpRequest('http://httpbin.org')
        mw.handle_request(req)
        assert req.headers.get('User-Agent') == user_agent

    def test_gen_user_agent(self):
        mw = UserAgentMiddleware.from_cluster(Cluster(user_agent=':desktop,chrome'))
        req = HttpRequest('http://httpbin.org')
        mw.handle_request(req)
        assert 'Chrome' in req.headers.get('User-Agent')

        mw2 = UserAgentMiddleware.from_cluster(Cluster(user_agent=':mobile,chrome'))
        req2 = HttpRequest('http://httpbin.org')
        mw2.handle_request(req2)
        assert 'CriOS' in req2.headers.get('User-Agent') and 'Mobile' in req2.headers.get('User-Agent')

    def test_unknown_user_agent_desciprtion(self):
        with pytest.raises(ValueError):
            UserAgentMiddleware.from_cluster(Cluster(user_agent=':unknown'))

    def test_random_user_agent(self):
        mw = UserAgentMiddleware.from_cluster(Cluster(random_user_agent=True))
        req = HttpRequest('http://httpbin.org')
        req2 = HttpRequest('http://httpbin.org')
        mw.handle_request(req)
        mw.handle_request(req2)
        assert 'User-Agent' in req.headers
        assert req.headers.get('User-Agent') != req2.headers.get('User-Agent')
        assert 'Chrome' in req.headers.get('User-Agent')

    def test_random_user_agent_under_selection(self):
        mw = UserAgentMiddleware.from_cluster(Cluster(user_agent=':mobile', random_user_agent=True))
        for i in range(30):
            req = HttpRequest('http://httpbin.org')
            mw.handle_request(req)
            assert 'User-Agent' in req.headers
            assert 'CriOS' in req.headers.get('User-Agent') and 'Mobile' in req.headers.get('User-Agent')
