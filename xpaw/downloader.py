# coding=utf-8

import logging
import asyncio
import inspect
from asyncio import CancelledError

import aiohttp

from .middleware import MiddlewareManager
from .http import HttpRequest, HttpResponse
from .errors import NetworkError
from .utils import parse_auth, parse_params, parse_url

log = logging.getLogger(__name__)


class Downloader:
    def __init__(self, timeout=None, verify_ssl=True, cookie_jar_enabled=False, loop=None):
        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._loop = loop or asyncio.get_event_loop()
        if cookie_jar_enabled:
            self._cookie_jar = aiohttp.CookieJar(loop=self._loop)
        else:
            self._cookie_jar = None

    async def download(self, request):
        log.debug("HTTP request: %s %s", request.method, request.url)
        timeout = request.meta.get("timeout")
        if not timeout:
            timeout = self._timeout
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=self._verify_ssl, loop=self._loop),
                                         cookies=request.cookies,
                                         cookie_jar=self._cookie_jar,
                                         loop=self._loop) as session:
            with aiohttp.Timeout(timeout, loop=self._loop):
                if isinstance(request.body, dict):
                    data, json = None, request.body
                else:
                    data, json = request.body, None
                async with session.request(request.method,
                                           parse_url(request.url),
                                           params=parse_params(request.params),
                                           auth=parse_auth(request.auth),
                                           headers=request.headers,
                                           data=data,
                                           json=json,
                                           proxy=parse_url(request.proxy),
                                           proxy_auth=parse_auth(request.proxy_auth)) as resp:
                    body = await resp.read()
                    cookies = resp.cookies
        response = HttpResponse(resp.url,
                                resp.status,
                                headers=resp.headers,
                                body=body,
                                cookies=cookies)
        log.debug("HTTP response: %s %s", response.url, response.status)
        return response


class DownloaderMiddlewareManager(MiddlewareManager):
    def __init__(self, *middlewares):
        self._request_handlers = []
        self._response_handlers = []
        self._error_handlers = []
        super().__init__(*middlewares)

    def _add_middleware(self, middleware):
        super()._add_middleware(middleware)
        if hasattr(middleware, "handle_request"):
            self._request_handlers.append(middleware.handle_request)
        if hasattr(middleware, "handle_response"):
            self._response_handlers.insert(0, middleware.handle_response)
        if hasattr(middleware, "handle_error"):
            self._error_handlers.insert(0, middleware.handle_error)

    @classmethod
    def _middleware_list_from_config(cls, config):
        return cls._make_component_list('downloader_middlewares', config)

    async def download(self, downloader, request):
        try:
            res = await self._handle_request(request)
            if isinstance(res, HttpRequest):
                return res
            if res is None:
                try:
                    response = await downloader.download(request)
                except CancelledError:
                    raise
                except Exception as e:
                    log.debug("Network error, %s: %s", type(e).__name__, e)
                    raise NetworkError(e)
                else:
                    res = response
        except CancelledError:
            raise
        except Exception as e:
            res = await self._handle_error(request, e)
            if isinstance(res, Exception):
                raise res
        if isinstance(res, HttpResponse):
            _res = await self._handle_response(request, res)
            if _res:
                res = _res
        return res

    async def _handle_request(self, request):
        for method in self._request_handlers:
            res = method(request)
            if inspect.iscoroutine(res):
                res = await res
            assert res is None or isinstance(res, (HttpRequest, HttpResponse)), \
                "Request handler must return None, HttpRequest or HttpResponse, got {}".format(type(res).__name__)
            if res:
                return res

    async def _handle_response(self, request, response):
        for method in self._response_handlers:
            res = method(request, response)
            if inspect.iscoroutine(res):
                res = await res
            assert res is None or isinstance(res, HttpRequest), \
                "Response handler must return None or HttpRequest, got {}".format(type(res).__name__)
            if res:
                return res

    async def _handle_error(self, request, error):
        for method in self._error_handlers:
            res = method(request, error)
            if inspect.iscoroutine(res):
                res = await res
            assert res is None or isinstance(res, (HttpRequest, HttpResponse)), \
                "Exception handler must return None, HttpRequest or HttpResponse, got {}".format(type(res).__name__)
            if res:
                return res
        return error
