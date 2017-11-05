# coding=utf-8

import logging
import inspect
from asyncio import CancelledError

from .middleware import MiddlewareManager
from . import events
from .utils import AsyncGenWrapper

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
    def _middleware_list_from_cluster(cls, cluster):
        mw_list = cluster.config.get("spider_middlewares")
        if mw_list:
            if not isinstance(mw_list, list):
                mw_list = [mw_list]
        else:
            mw_list = []
        log.info("Spider middlewares: %s", mw_list)
        return mw_list

    async def parse(self, spider, response):
        try:
            await self._handle_input(response)
            if response.request and response.request.callback:
                r = getattr(spider, response.request.callback)(response)
            else:
                r = spider.parse(response)
            if inspect.iscoroutine(r):
                r = await r
            assert r is None or _isiterable(r), \
                "Result of parsing must be None or an iterable object, got {}".format(type(r).__name__)
            if r:
                r = await self._handle_output(response, r)
            if r is None:
                r = ()
            if not hasattr(r, "__aiter__"):
                r = AsyncGenWrapper(r, errback=lambda x, resp=response: self._handle_error_of_parse(resp, x))
            return r
        except CancelledError:
            raise
        except Exception as e:
            return await self._handle_error_of_parse(response, e)

    async def _handle_error_of_parse(self, response, error):
        res = await self._handle_error(response, error)
        if isinstance(res, Exception):
            raise res
        return res or ()

    async def handle_error(self, spider, request, error):
        if request and request.errback:
            r = getattr(spider, request.errback)(request, error)
            if inspect.iscoroutine(r):
                await r

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
