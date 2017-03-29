# coding=utf-8

from xpaw.downloadermws.cookies import CookieJarMiddleware
from xpaw.downloadermws.forward import ForwardedForMiddleware
from xpaw.downloadermws.headers import RequestHeadersMiddleware
from xpaw.downloadermws.proxy import ProxyMiddleware, ProxyAgentMiddleware
from xpaw.downloadermws.retry import RetryMiddleware, ResponseMatchMiddleware
from xpaw.downloadermws.speed import SpeedLimitMiddleware
