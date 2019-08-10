# coding=utf-8


import pytest

from xpaw.http import HttpRequest
from xpaw.extensions import UserAgentMiddleware

from ..crawler import Crawler


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
