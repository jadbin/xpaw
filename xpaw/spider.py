# coding=utf-8

import logging
import inspect
from asyncio import CancelledError

from .middleware import MiddlewareManager
from . import events
from .utils import AsyncGenWrapper, iterable_to_list

log = logging.getLogger(__name__)


class Spider:
    def __init__(self, config=None, cluster=None):
        self.config = config
        self.cluster = cluster

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
                await self.handle_error(spider, request, e)
                raise e
            if request.callback:
                res = getattr(spider, request.callback)(response)
            else:
                res = spider.parse(response)
            if inspect.iscoroutine(res):
                res = await res
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

    @staticmethod
    async def handle_error(spider, request, error):
        try:
            if request and request.errback:
                r = getattr(spider, request.errback)(request, error)
                if inspect.iscoroutine(r):
                    await r
        except CancelledError:
            raise
        except Exception:
            log.warning("Error occurred in error callback", exc_info=True)

    async def start_requests(self, spider):
        r = spider.start_requests()
        assert r is None or _isiterable(r), \
            "Start requests must be None or an iterable object, got {}".format(type(r).__name__)
        if r:
            r = await self._handle_start_requests(r)
        if r is None:
            r = ()
        if not hasattr(r, "__aiter__"):
            r = AsyncGenWrapper(r)
        return r

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
