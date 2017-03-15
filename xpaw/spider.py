# coding=utf-8

import logging

from xpaw.middleware import MiddlewareManager

log = logging.getLogger(__name__)


class Spider:
    def __init__(self, config):
        self.config = config

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
        super().__init__(self, *middlewares)

    def _add_middleware(self, middleware):
        if hasattr(middleware, "handle_input"):
            self._input_handlers.append(middleware.handle_input)
        if hasattr(middleware, "handle_output"):
            self._output_handlers.append(middleware.handle_output)
        if hasattr(middleware, "handle_error"):
            self._error_handlers.append(middleware.handle_error)
        if hasattr(middleware, "handle_start_requests"):
            self._start_requests_handlers.append(middleware.handle_start_requests)

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
        except Exception as e:
            try:
                self._handle_error(response, e)
                yield e
            except Exception as _e:
                yield _e
        else:
            if r is None:
                return ()
            for i in r:
                yield i

    def start_requests(self, spider):
        try:
            r = spider.start_requests()
            if r:
                r = self._handle_start_requests(r)
        except Exception as e:
            yield e
        else:
            if r is None:
                return ()
            for i in r:
                yield i

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
            if res is not None:
                raise TypeError("Exception handler must return None, got {}".format(type(res)))

    def _handle_start_requests(self, result):
        for method in self._start_requests_handlers:
            result = method(result)
            if not _isiterable(result):
                raise TypeError("Start requests handler must return an iterable object, got {}".format(type(result)))
        return result
