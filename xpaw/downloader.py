# coding=utf-8

import logging
import asyncio
import inspect
from asyncio import CancelledError
from urllib.parse import urlsplit

import aiohttp
import async_timeout
from yarl import URL
from multidict import MultiDict
from aiohttp.helpers import BasicAuth

from .middleware import MiddlewareManager
from .http import HttpRequest, HttpResponse
from .errors import NetworkError

log = logging.getLogger(__name__)


class Downloader:
    def __init__(self, timeout=None, verify_ssl=False, allow_redirects=True, loop=None):
        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._allow_redirects = allow_redirects
        self._loop = loop or asyncio.get_event_loop()

    async def download(self, request):
        log.debug("HTTP request: %s", request)
        timeout = request.meta.get("timeout")
        if timeout is None:
            timeout = self._timeout
        verify_ssl = request.meta.get('verify_ssl')
        if verify_ssl is None:
            verify_ssl = self._verify_ssl
        allow_redirects = request.meta.get('allow_redirects')
        if allow_redirects is None:
            allow_redirects = self._allow_redirects
        cookie_jar = request.meta.get('cookie_jar')
        auth = parse_request_auth(request.meta.get('auth'))
        proxy = parse_request_url(request.meta.get('proxy'))
        proxy_auth = parse_request_auth(request.meta.get('proxy_auth'))
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=verify_ssl, loop=self._loop),
                                         cookies=request.cookies,
                                         cookie_jar=cookie_jar,
                                         loop=self._loop) as session:
            with async_timeout.timeout(timeout, loop=self._loop):
                if isinstance(request.body, dict):
                    data, json = None, request.body
                else:
                    data, json = request.body, None
                async with session.request(request.method,
                                           parse_request_url(request.url),
                                           params=parse_request_params(request.params),
                                           auth=auth,
                                           headers=request.headers,
                                           data=data,
                                           json=json,
                                           proxy=proxy,
                                           proxy_auth=proxy_auth,
                                           allow_redirects=allow_redirects) as resp:
                    body = await resp.read()
                    cookies = resp.cookies
        response = HttpResponse(resp.url,
                                resp.status,
                                headers=resp.headers,
                                body=body,
                                cookies=cookies)
        log.debug("HTTP response: %s", response)
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
                    log.debug("Network error: %s", e)
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
            # bind request
            res.request = request
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


def parse_request_params(params):
    if isinstance(params, dict):
        res = MultiDict()
        for k, v in params.items():
            if isinstance(v, (tuple, list)):
                for i in v:
                    res.add(k, i)
            else:
                res.add(k, v)
        params = res
    return params


def parse_request_auth(auth):
    if isinstance(auth, (tuple, list)):
        auth = BasicAuth(*auth)
    elif isinstance(auth, str):
        auth = BasicAuth(*auth.split(':', 1))
    return auth


def parse_request_url(url):
    if isinstance(url, str):
        res = urlsplit(url)
        if res.scheme == '':
            url = 'http://{}'.format(url)
        url = URL(url)
    return url
