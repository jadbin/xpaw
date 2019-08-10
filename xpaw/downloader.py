# coding=utf-8

import logging
from asyncio import CancelledError
from urllib.parse import urlsplit
from asyncio import Semaphore

from tornado.httpclient import HTTPRequest, HTTPClientError
from tornado.curl_httpclient import CurlAsyncHTTPClient

import pycurl

from .http import HttpResponse
from .errors import ClientError, HttpError
from . import events
from .renderer import ChromeRenderer
from .utils import with_not_none_params

log = logging.getLogger(__name__)


class Downloader:
    def __init__(self, max_clients=100, renderer=None, renderer_cores=None):
        self._max_clients = max_clients
        self._http_client = CurlAsyncHTTPClient(max_clients=max_clients, force_instance=True)
        self._renderer = renderer
        if renderer_cores is None:
            renderer_cores = self._max_clients
        self._renderer_semaphore = Semaphore(renderer_cores)

    @classmethod
    def from_crawler(cls, crawler):
        config = crawler.config
        renderer = ChromeRenderer(options=config.get('chrome_renderer_options'))
        downloader = cls(**with_not_none_params(max_clients=config.getint('downloader_clients'),
                                                renderer=renderer,
                                                renderer_cores=config.getint('renderer_cores')))
        crawler.event_bus.subscribe(downloader.close, events.crawler_shutdown)
        return downloader

    @property
    def max_clients(self):
        return self._max_clients

    async def fetch(self, request):
        log.debug("HTTP request: %s", request)
        try:
            if request.render:
                async with self._renderer_semaphore:
                    response = await self._renderer.fetch(request)
            else:
                req = self._make_request(request)
                resp = await self._http_client.fetch(req)
                response = self._make_response(resp)
        except CancelledError:
            raise
        except HTTPClientError as e:
            if e.response is not None and e.response.code != 599:
                raise HttpError('{} {}'.format(e.response.code, e.message),
                                response=self._make_response(e.response))
            raise ClientError(e.message)
        except Exception as e:
            raise ClientError(e)
        log.debug("HTTP response: %s", response)
        return response

    def _make_request(self, request):
        kwargs = {'method': request.method,
                  'headers': request.headers,
                  'body': request.body,
                  'connect_timeout': request.timeout,  # FIXME
                  'request_timeout': request.timeout,  # FIXME
                  'follow_redirects': request.allow_redirects,
                  'validate_cert': request.verify_ssl}
        if request.auth is not None:
            auth_username, auth_password = request.auth
            kwargs['auth_username'] = auth_username
            kwargs['auth_password'] = auth_password
        if request.proxy is not None:
            s = urlsplit(request.proxy)
            if s.scheme:
                if s.scheme in ('http', 'socks4', 'socks5'):
                    proxy_host, proxy_port = s.hostname, s.port
                else:
                    raise ValueError('Unsupported proxy scheme: {}'.format(s.scheme))
                if s.scheme == 'socks5':
                    kwargs['prepare_curl_callback'] = prepare_curl_socks5
                elif s.scheme == 'socks4':
                    kwargs['prepare_curl_callback'] = prepare_curl_socks4
            else:
                proxy_host, proxy_port = request.proxy.split(':')
            kwargs['proxy_host'] = proxy_host
            kwargs['proxy_port'] = int(proxy_port)
        if request.proxy_auth is not None:
            proxy_username, proxy_password = request.proxy_auth
            kwargs['proxy_username'] = proxy_username
            kwargs['proxy_password'] = proxy_password
        return HTTPRequest(request.url, **kwargs)

    def _make_response(self, resp):
        return HttpResponse(resp.effective_url,
                            resp.code,
                            headers=resp.headers,
                            body=resp.body)

    def close(self):
        self._http_client.close()
        self._renderer.close()


def prepare_curl_socks5(curl):
    curl.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS5)


def prepare_curl_socks4(curl):
    curl.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS4)
