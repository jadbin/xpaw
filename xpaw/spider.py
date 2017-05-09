# coding=utf-8

import logging

from xpaw.middleware import MiddlewareManager

log = logging.getLogger(__name__)


class Spider:
    def __init__(self, config):
        self.config = config

    @property
    def logger(self):
        return log

    def log(self, message, level=logging.INFO, **kw):
        self.logger.log(level, message, **kw)

    def parse(self, response):
        raise NotImplementedError

    def start_requests(self):
        raise NotImplementedError


def _isiterable(obj):
    return hasattr(obj, "__iter__")


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
        mw_list = config.get("spider_middlewares")
        if mw_list:
            if not isinstance(mw_list, list):
                mw_list = [mw_list]
        else:
            mw_list = []
        log.debug("Spider middleware list: {}".format(mw_list))
        return mw_list

    def parse(self, spider, response):
        try:
            self._handle_input(response)
            if response.request and response.request.callback:
                r = getattr(spider, response.request.callback)(response)
            else:
                r = spider.parse(response)
            if r:
                r = self._handle_output(response, r)
            if r is None:
                return ()
            for i in r:
                yield i
        except Exception as e:
            handled = self._handle_error(response, e)
            if handled is not True:
                raise e

    def handle_error(self, spider, request, error):
        if request and request.errback:
            getattr(spider, request.errback)(request, error)

    def start_requests(self, spider):
        try:
            r = spider.start_requests()
            if r:
                r = self._handle_start_requests(r)
            if r is None:
                return ()
            for i in r:
                yield i
        except Exception as e:
            raise e

    def _handle_input(self, response):
        for method in self._input_handlers:
            res = method(response)
            if res is not None:
                raise TypeError("Input handler must return None, got {}".format(type(res)))

    def _handle_output(self, response, result):
        for method in self._output_handlers:
            result = method(response, result)
            if not _isiterable(result):
                raise TypeError("Response handler must return an iterable object, got {}".format(type(result)))
        return result

    def _handle_error(self, response, error):
        for method in self._error_handlers:
            res = method(response, error)
            if not (res is None or res is True):
                raise TypeError("Exception handler must return None or True, got {}".format(type(res)))
            if res is not None:
                return res

    def _handle_start_requests(self, result):
        for method in self._start_requests_handlers:
            result = method(result)
            if not _isiterable(result):
                raise TypeError("Start requests handler must return an iterable object, got {}".format(type(result)))
        return result
