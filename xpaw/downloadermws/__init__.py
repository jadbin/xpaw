# coding=utf-8

from xpaw.downloadermws.cookies import CookieJarMiddleware
from xpaw.downloadermws.headers import RequestHeadersMiddleware, ForwardedForMiddleware
from xpaw.downloadermws.proxy import ProxyMiddleware, ProxyAgentMiddleware
from xpaw.downloadermws.retry import RetryMiddleware, ResponseMatchMiddleware
from xpaw.downloadermws.speed import SpeedLimitMiddleware
