# coding=utf-8

import logging
import asyncio

import aiohttp
import async_timeout

from xpaw.middleware import MiddlewareManager
from xpaw.http import HttpRequest, HttpResponse
from xpaw.errors import NetworkError

log = logging.getLogger(__name__)


class Downloader:
    def __init__(self, timeout=None, loop=None):
        self._timeout = timeout
        self._loop = loop or asyncio.get_event_loop()

    async def download(self, request):
        log.debug("HTTP request: {} {}".format(request.method, request.url))
        timeout = request.meta.get("timeout")
        if not timeout:
            timeout = self._timeout
        async with aiohttp.ClientSession(cookies=request.cookies,
                                         loop=self._loop,
                                         cookie_jar=request.meta.get("cookie_jar")) as session:
            with async_timeout.timeout(timeout, loop=self._loop):
                async with session.request(request.method,
                                           request.url,
                                           headers=request.headers,
                                           data=request.body,
                                           proxy=request.proxy) as resp:
                    body = await resp.read()
                    cookies = resp.cookies
        response = HttpResponse(resp.url,
                                resp.status,
                                headers=resp.headers,
                                body=body,
                                cookies=cookies)
        log.debug("HTTP response: {} {}".format(response.url, response.status))
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
            self._request_handlers.append(self._coro_wrapper(middleware.handle_request))
        if hasattr(middleware, "handle_response"):
            self._response_handlers.insert(0, self._coro_wrapper(middleware.handle_response))
        if hasattr(middleware, "handle_error"):
            self._error_handlers.insert(0, self._coro_wrapper(middleware.handle_error))

    def _coro_wrapper(self, func):
        if asyncio.iscoroutinefunction(func):
            return func

        async def coro_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            return result

        return coro_wrapper

    @classmethod
    def _middleware_list_from_config(cls, config):
        mw_list = config.get("downloader_middlewares")
        if mw_list:
            if not isinstance(mw_list, list):
                mw_list = [mw_list]
        else:
            mw_list = []
        log.debug("Downloader middleware list: {}".format(mw_list))
        return mw_list

    async def download(self, downloader, request):
        try:
            res = await self._handle_request(request)
            if isinstance(res, HttpRequest):
                return res
            if res is None:
                try:
                    response = await downloader.download(request)
                except Exception as e:
                    log.debug("Network error {}: {}".format(type(e), e))
                    raise NetworkError(e)
                else:
                    res = response
            _res = await self._handle_response(request, res)
            if _res:
                res = _res
        except Exception as e:
            res = await self._handle_error(request, e)
            if res is not True:
                if res:
                    return res
                raise e
        else:
            return res

    async def _handle_request(self, request):
        for method in self._request_handlers:
            res = await method(request)
            if not (res is None or isinstance(res, (HttpRequest, HttpResponse))):
                raise TypeError("Request handler must return None, HttpRequest or HttpResponse,"
                                " got {}".format(type(res)))
            if res:
                return res

    async def _handle_response(self, request, response):
        for method in self._response_handlers:
            res = await method(request, response)
            if not (res is None or isinstance(res, HttpRequest)):
                raise TypeError("Response handler must return None or HttpRequest,"
                                " got {}".format(type(res)))
            if res:
                return res

    async def _handle_error(self, request, error):
        for method in self._error_handlers:
            res = await method(request, error)
            if not (res is None or res is True or isinstance(res, (HttpRequest, HttpResponse))):
                raise TypeError("Exception handler must return None, True, HttpRequest or HttpResponse,"
                                " got {}".format(type(res)))
            if res is not None:
                return res
