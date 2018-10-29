# coding=utf-8

import logging
import inspect
from asyncio import CancelledError
from urllib.parse import urlsplit

from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPClientError
from tornado.httputil import url_concat

from .middleware import MiddlewareManager
from .http import HttpRequest, HttpResponse, HttpHeaders
from .errors import ClientError, RequestTimeout, HttpError

log = logging.getLogger(__name__)


class Downloader:
    def __init__(self, max_clients=10):
        self._max_clients = max_clients
        self._http_client = AsyncHTTPClient(max_clients=max_clients)

    @property
    def max_clients(self):
        return self._max_clients

    async def download(self, request):
        log.debug("HTTP request: %s", request)
        req = self._make_request(request)
        try:
            resp = await self._http_client.fetch(req)
        except HTTPClientError as e:
            if e.code == 599:
                log.debug('%s is timeout', request)
                raise RequestTimeout
            elif e.response is not None:
                raise HttpError(response=self._make_response(e.response))
            raise
        response = self._make_response(resp)
        log.debug("HTTP response: %s", response)
        return response

    @classmethod
    def _make_request(cls, request):
        url = url_concat(cls._make_request_url(request.url), request.params)
        kwargs = {'method': request.method,
                  'headers': cls._make_request_headers(request.headers),
                  'body': request.body,
                  'request_timeout': request.timeout,
                  'follow_redirects': request.allow_redirects,
                  'validate_cert': request.verify_ssl}
        if request.auth is not None:
            auth_username, auth_password = request.auth
            kwargs['auth_username'] = auth_username
            kwargs['auth_password'] = auth_password
        if request.proxy is not None:
            proxy = urlsplit(cls._make_request_url(request.proxy))
            kwargs['proxy_host'] = proxy.hostname
            kwargs['proxy_port'] = proxy.port
        if request.proxy_auth is not None:
            proxy_username, proxy_password = request.proxy_auth
            kwargs['proxy_username'] = proxy_username
            kwargs['proxy_password'] = proxy_password
        return HTTPRequest(url, **kwargs)

    @staticmethod
    def _make_response(resp):
        return HttpResponse(resp.effective_url,
                            resp.code,
                            headers=resp.headers,
                            body=resp.body)

    @staticmethod
    def _make_request_headers(headers):
        res = HttpHeaders()
        if isinstance(headers, dict):
            for k, v in headers.items():
                if isinstance(v, (tuple, list)):
                    for i in v:
                        res.add(k, i)
                else:
                    res.add(k, v)
        elif isinstance(headers, (tuple, list)):
            for k, v in headers:
                res.add(k, v)
        return res

    @staticmethod
    def _make_request_url(url):
        if isinstance(url, str):
            res = urlsplit(url)
            if res.scheme == '':
                url = 'http://{}'.format(url)
        return url


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
                except (CancelledError, RequestTimeout, HttpError):
                    raise
                except Exception as e:
                    log.debug("%s is error: %s", request, e)
                    raise ClientError(e)
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
