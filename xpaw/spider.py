# coding=utf-8

import logging
import inspect
from asyncio import CancelledError

from .middleware import MiddlewareManager
from . import events
from .utils import iterable_to_list
from .http import HttpRequest

log = logging.getLogger(__name__)


class Spider:
    def __init__(self, config=None, **kwargs):
        self.config = config
        self.__dict__.update(kwargs)

    @classmethod
    def from_cluster(cls, cluster):
        spider = cls(config=cluster.config, cluster=cluster)
        cluster.event_bus.subscribe(spider.open, events.cluster_start)
        cluster.event_bus.subscribe(spider.close, events.cluster_shutdown)
        return spider

    @property
    def logger(self):
        return log

    def log(self, message, *args, level=logging.INFO, **kwargs):
        self.logger.log(level, message, *args, **kwargs)

    def parse(self, response):
        raise NotImplementedError

    def start_requests(self):
        raise NotImplementedError

    def open(self):
        pass

    def close(self):
        pass

    async def request_success(self, response):
        callback = response.request.callback
        if callback:
            res = self._parse_method(callback)(response)
        else:
            res = self.parse(response)
        if inspect.iscoroutine(res):
            res = await res
        return res

    async def request_error(self, request, error):
        try:
            if request and request.errback:
                r = self._parse_method(request.errback)(request, error)
                if inspect.iscoroutine(r):
                    await r
        except CancelledError:
            raise
        except Exception as e:
            log.warning("Error occurred in error callback: %s", e)

    def _parse_method(self, method):
        if isinstance(method, str):
            method = getattr(self, method)
        return method


def _isiterable(obj):
    return hasattr(obj, "__iter__") or hasattr(obj, "__aiter__")


class SpiderMiddlewareManager(MiddlewareManager):
    def __init__(self, *middlewares):
        self._input_handlers = []
        self._output_handlers = []
        self._error_handlers = []
        self._start_requests_handlers = []
        super().__init__(*middlewares)

    def _add_middleware(self, middleware):
        super()._add_middleware(middleware)
        if hasattr(middleware, "handle_input"):
            self._input_handlers.append(middleware.handle_input)
        if hasattr(middleware, "handle_output"):
            self._output_handlers.insert(0, middleware.handle_output)
        if hasattr(middleware, "handle_error"):
            self._error_handlers.insert(0, middleware.handle_error)
        if hasattr(middleware, "handle_start_requests"):
            self._start_requests_handlers.insert(0, middleware.handle_start_requests)

    @classmethod
    def _middleware_list_from_config(cls, config):
        return cls._make_component_list('spider_middlewares', config)

    async def parse(self, spider, response):
        request = response.request
        try:
            try:
                await self._handle_input(response)
            except CancelledError:
                raise
            except Exception as e:
                await spider.request_error(request, e)
                raise e
            res = await spider.request_success(response)
            assert res is None or _isiterable(res), \
                "Parsing result must be None or an iterable object, got {}".format(type(res).__name__)
            result = await iterable_to_list(res)
        except CancelledError:
            raise
        except Exception as e:
            res = await self._handle_error(response, e)
            if isinstance(res, Exception):
                raise res
            result = await iterable_to_list(res)
        if result:
            res = await self._handle_output(response, result)
            result = await iterable_to_list(res)
        return result

    async def start_requests(self, spider):
        res = spider.start_requests()
        if inspect.iscoroutine(res):
            res = await res
        assert res is None or _isiterable(res), \
            "Start requests must be None or an iterable object, got {}".format(type(res).__name__)
        result = await iterable_to_list(res)
        if result:
            res = await self._handle_start_requests(result)
            result = await iterable_to_list(res)
        return result

    async def _handle_input(self, response):
        for method in self._input_handlers:
            res = method(response)
            if inspect.iscoroutine(res):
                res = await res
            assert res is None, \
                "Input handler must return None, got {}".format(type(res).__name__)

    async def _handle_output(self, response, result):
        for method in self._output_handlers:
            result = method(response, result)
            if inspect.iscoroutine(result):
                result = await result
            assert _isiterable(result), \
                "Output handler must return an iterable object, got {}".format(type(result).__name__)
        return result

    async def _handle_error(self, response, error):
        for method in self._error_handlers:
            res = method(response, error)
            if inspect.iscoroutine(res):
                res = await res
            assert res is None or _isiterable(res), \
                "Exception handler must return None or an iterable object, got {}".format(type(res).__name__)
            if res is not None:
                return res
        return error

    async def _handle_start_requests(self, result):
        for method in self._start_requests_handlers:
            result = method(result)
            if inspect.iscoroutine(result):
                result = await result
            assert _isiterable(result), \
                "Start requests handler must return an iterable object, got {}".format(type(result).__name__)
        return result


def every(hours=None, minutes=None, seconds=None):
    def wrapper(func):
        func.cron_job = True
        func.cron_tick = hours * 3600 + minutes * 60 + seconds
        return func

    if hours is None and minutes is None and seconds is None:
        raise ValueError('At least one of the parameters (hours, minutes and seconds) is not none')
    if hours is None:
        hours = 0
    if minutes is None:
        minutes = 0
    if seconds is None:
        seconds = 0
    return wrapper


class RequestsSpider(Spider):
    def start_requests(self):
        requests = self.config.get('start_requests')
        i = 0
        for r in requests:
            if isinstance(r, str):
                r = HttpRequest(r)
            if isinstance(r, HttpRequest):
                r.meta['request_index'] = i
                r.dont_filter = True
                r.callback = self.parse
                r.errback = self.handle_error
                yield r
            else:
                self.logger.warning('Requests must be str or HttpRequest, got %s', type(r).__name__)
            i += 1

    def parse(self, response):
        results = self.config.get('results')
        results[response.meta['request_index']] = response

    def handle_error(self, request, err):
        results = self.config.get('results')
        results[request.meta['request_index']] = err
