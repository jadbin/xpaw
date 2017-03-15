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
    def __init__(self, loop=None):
        self._loop = loop or asyncio.get_event_loop()

    async def download(self, request, timeout=None):
        log.debug("HTTP request: {} {}".format(request.method, request.url))
        with aiohttp.ClientSession(cookies=request.cookies, loop=self._loop) as session:
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
        return response


class DownloaderMiddlewareManager(MiddlewareManager):
    def __init__(self, *middlewares):
        self._request_handlers = []
        self._response_handlers = []
        self._error_handlers = []
        super().__init__(self, *middlewares)

    def _add_middleware(self, middleware):
        if hasattr(middleware, "handle_request"):
            self._request_handlers.append(middleware.handle_request)
        if hasattr(middleware, "handle_response"):
            self._response_handlers.append(middleware.handle_response)
        if hasattr(middleware, "handle_error"):
            self._error_handlers.append(middleware.handle_error)

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

    async def download(self, downloader, request, timeout=None):
        try:
            res = await self._handle_request(request)
            if isinstance(res, HttpRequest):
                return res
            if res is None:
                try:
                    response = await downloader.download(request, timeout=timeout)
                    log.debug("HTTP response: {} {}".format(response.url, response.status))
                except Exception as e:
                    log.debug("Network error {}: {}".format(type(e), e))
                    raise NetworkError(e)
                else:
                    res = response
            _res = await self._handle_response(request, res)
            if _res:
                res = _res
        except Exception as e:
            try:
                res = await self._handle_error(request, e)
            except Exception:
                raise
            else:
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
        handled = False
        for method in self._error_handlers:
            res = await method(request, error)
            if not (res is None or res is True or isinstance(res, (HttpRequest, HttpResponse))):
                raise TypeError("Exception handler must return None, True, HttpRequest or HttpResponse,"
                                " got {}".format(type(res)))
            if res is True:
                handled = True
            elif res:
                return res
        return handled
