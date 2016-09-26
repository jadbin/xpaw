# coding=utf-8

import logging
import asyncio

import aiohttp

from xpaw.middleware import MiddlewareManager
from xpaw.http import HttpRequest, HttpResponse
from xpaw.errors import NetworkError

log = logging.getLogger(__name__)


class Downloader:
    def __init__(self, *, clients=100, timeout=20, loop=None):
        self._loop = loop or asyncio.get_event_loop()
        self._clients = asyncio.Semaphore(clients, loop=self._loop)
        self._timeout = timeout

    @classmethod
    def from_config(cls, config):
        kw = {}
        if "downloader_clients" in config:
            kw["clients"] = config["downloader_clients"]
        if "downloader_timeout" in config:
            kw["timeout"] = config["downloader_timeout"]
        kw["loop"] = config.get("_downloader_loop")
        return cls(**kw)

    async def add_task(self, request, callback, *, timeout=None, middleware=None):
        if not timeout:
            timeout = self._timeout
        await self._clients.acquire()
        asyncio.ensure_future(self._task(request, callback, timeout, middleware), loop=self._loop)

    async def _task(self, request, callback, timeout, middleware):
        async def _handle():
            try:
                res = None
                if middleware:
                    res = await self._handle_request(request, middleware)
                if isinstance(res, HttpRequest):
                    return res
                if res is None:
                    try:
                        response = await self._get(request, timeout)
                        log.debug("HTTP response: {0} {1}".format(response.url, response.status))
                    except Exception as e:
                        log.debug("Network error {0}: {1}".format(type(e), e))
                        raise NetworkError(e)
                    else:
                        res = response
                if middleware:
                    _res = await self._handle_response(request, res, middleware)
                    if _res:
                        res = _res
            except Exception as e:
                try:
                    res = None
                    if middleware:
                        res = await self._handle_error(request, e, middleware)
                except Exception as _e:
                    return _e
                else:
                    return res or e
            else:
                return res

        result = await _handle()
        try:
            callback(request, result)
        except Exception:
            log.warning("Unexpected error occurred in callback", exc_info=True)
        finally:
            self._clients.release()

    @staticmethod
    async def _handle_request(request, middleware):
        for method in middleware.request_handlers:
            res = await method(request)
            if not (res is None or isinstance(res, (HttpRequest, HttpResponse))):
                raise TypeError("Request handler must return None, HttpRequest or HttpResponse, got {0}".format(type(res)))
            if res:
                return res

    @staticmethod
    async def _handle_response(request, response, middleware):
        for method in middleware.response_handlers:
            res = await method(request, response)
            if not (res is None or isinstance(res, HttpRequest)):
                raise TypeError("Response handler must return None or HttpRequest, got {0}".format(type(res)))
            if res:
                return res

    @staticmethod
    async def _handle_error(request, error, middleware):
        for method in middleware.error_handlers:
            res = await method(request, error)
            if not (res is None or isinstance(res, HttpRequest)):
                raise TypeError("Exception handler must return None or HttpRequest, got {0}".format(type(res)))
            if res:
                return res

    async def _get(self, request, timeout):
        log.debug("HTTP request: {0} {1}".format(request.method, request.url))
        with aiohttp.ClientSession(cookies=request.cookies, loop=self._loop) as session:
            with aiohttp.Timeout(timeout, loop=self._loop):
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

    @property
    def request_handlers(self):
        return self._request_handlers

    @property
    def response_handlers(self):
        return self._response_handlers

    @property
    def error_handlers(self):
        return self._error_handlers

    @classmethod
    def _middleware_list_from_config(cls, config):
        mw_list = config.get("downloader_middlewares")
        if mw_list:
            if not isinstance(mw_list, list):
                mw_list = [mw_list]
        else:
            mw_list = []
        log.debug("Downloader middleware list: {0}".format(mw_list))
        return mw_list
