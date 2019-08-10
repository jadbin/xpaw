# coding=utf-8

import logging
import inspect

from .utils import load_object, isiterable
from . import events
from .errors import NotEnabled
from .http import HttpRequest, HttpResponse, HttpHeaders, _HttpHeaders

log = logging.getLogger(__name__)


class ExtensionManager:
    def __init__(self, *extensions):
        self._open_handlers = []
        self._close_handlers = []

        self._request_handlers = []
        self._response_handlers = []
        self._error_handlers = []

        self._spider_input_handlers = []
        self._spider_output_handlers = []
        self._spider_error_handlers = []
        self._start_requests_handlers = []

        self._item_handlers = []

        self.components = []
        for ext in extensions:
            self._add_extension(ext)

    @classmethod
    def _extension_list_from_config(cls, config):
        return cls._make_component_list('extensions', config)

    @classmethod
    def from_crawler(cls, crawler):
        ext_list = cls._extension_list_from_config(crawler.config)
        exts = []
        for cls_path in ext_list:
            ext_cls = load_object(cls_path)
            try:
                if hasattr(ext_cls, "from_crawler"):
                    ext = ext_cls.from_crawler(crawler)
                else:
                    ext = ext_cls()
            except NotEnabled:
                log.debug('%s is not enabled', cls_path)
            else:
                exts.append(ext)
        obj = cls(*exts)
        crawler.event_bus.subscribe(obj.open, events.crawler_start)
        crawler.event_bus.subscribe(obj.close, events.crawler_shutdown)
        return obj

    def _add_extension(self, ext):
        self.components.append(ext)
        if hasattr(ext, "open"):
            self._open_handlers.append(ext.open)
        if hasattr(ext, "close"):
            self._close_handlers.insert(0, ext.close)

        if hasattr(ext, "handle_request"):
            self._request_handlers.append(ext.handle_request)
        if hasattr(ext, "handle_response"):
            self._response_handlers.insert(0, ext.handle_response)
        if hasattr(ext, "handle_error"):
            self._error_handlers.insert(0, ext.handle_error)

        if hasattr(ext, "handle_spider_input"):
            self._spider_input_handlers.append(ext.handle_spider_input)
        if hasattr(ext, "handle_spider_output"):
            self._spider_output_handlers.insert(0, ext.handle_spider_output)
        if hasattr(ext, "handle_spider_error"):
            self._spider_error_handlers.insert(0, ext.handle_spider_error)

        if hasattr(ext, "handle_start_requests"):
            self._start_requests_handlers.insert(0, ext.handle_start_requests)
        if hasattr(ext, "handle_item"):
            self._item_handlers.append(ext.handle_item)

    @staticmethod
    def _list_from_config(name, config):
        c = config.get(name)
        assert c is None or isinstance(c, list), \
            "'{}' must be None or a list, got {}".format(name, type(c).__name__)
        if c is None:
            return []
        return c

    @classmethod
    def _make_component_list(cls, name, config):
        c_base = cls._list_from_config('default_' + name, config)
        c = cls._list_from_config(name, config)
        return c + c_base

    def open(self):
        for method in self._open_handlers:
            method()

    def close(self):
        for method in self._close_handlers:
            method()

    async def handle_request(self, request):
        request.headers = self._make_request_headers(request.headers)
        for method in self._request_handlers:
            res = method(request)
            if inspect.iscoroutine(res):
                res = await res
            assert res is None or isinstance(res, (HttpRequest, HttpResponse)), \
                "Request handler must return None, HttpRequest or HttpResponse, got {}".format(type(res).__name__)
            if res:
                return res

    def _make_request_headers(self, headers):
        if isinstance(headers, (HttpHeaders, _HttpHeaders)):
            return headers
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

    async def handle_response(self, request, response):
        for method in self._response_handlers:
            res = method(request, response)
            if inspect.iscoroutine(res):
                res = await res
            assert res is None or isinstance(res, HttpRequest), \
                "Response handler must return None or HttpRequest, got {}".format(type(res).__name__)
            if res:
                return res

    async def handle_error(self, request, error):
        for method in self._error_handlers:
            res = method(request, error)
            if inspect.iscoroutine(res):
                res = await res
            assert res is None or isinstance(res, (HttpRequest, HttpResponse)), \
                "Exception handler must return None, HttpRequest or HttpResponse, got {}".format(type(res).__name__)
            if res:
                return res
        return error

    async def handle_spider_input(self, response):
        for method in self._spider_input_handlers:
            res = method(response)
            if inspect.iscoroutine(res):
                res = await res
            assert res is None, \
                "Spider input handler must return None, got {}".format(type(res).__name__)

    async def handle_spider_output(self, response, result):
        for method in self._spider_output_handlers:
            result = method(response, result)
            if inspect.iscoroutine(result):
                result = await result
            assert isiterable(result), \
                "Spider output handler must return an iterable object, got {}".format(type(result).__name__)
        return result

    async def handle_spider_error(self, response, error):
        for method in self._spider_error_handlers:
            res = method(response, error)
            if inspect.iscoroutine(res):
                res = await res
            assert res is None or isiterable(res), \
                "Spider exception handler must return None or an iterable object, got {}".format(type(res).__name__)
            if res is not None:
                return res
        return error

    async def handle_start_requests(self, result):
        for method in self._start_requests_handlers:
            result = method(result)
            if inspect.iscoroutine(result):
                result = await result
            assert isiterable(result), \
                "Start requests handler must return an iterable object, got {}".format(type(result).__name__)
        return result

    async def handle_item(self, item):
        log.debug('Item (%s): %s', type(item).__name__, item)
        for method in self._item_handlers:
            res = method(item)
            if inspect.iscoroutine(res):
                await res
