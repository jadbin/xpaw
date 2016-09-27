# coding=utf-8

import logging

from xpaw.helpers import load_object
from xpaw.middleware import MiddlewareManager

log = logging.getLogger(__name__)


class Spider:
    def __init__(self, *spiders):
        self._start_requests_handlers = []
        self._parse_handlers = []
        for spider in spiders:
            self._add_spider(spider)

    @classmethod
    def from_config(cls, config):
        spider_list = config.get("spiders", [])
        if not isinstance(spider_list, list):
            spider_list = [spider_list]
        log.debug("Spider list: {0}".format(spider_list))
        spiders = []
        for cls_path in spider_list:
            try:
                spider_cls = load_object(cls_path)
                if hasattr(spider_cls, "from_config"):
                    spider = spider_cls.from_config(config)
                else:
                    spider = spider_cls()
            except Exception:
                log.warning("Unexpected error occurred when load spider '{0}'".format(cls_path), exc_info=True)
            else:
                spiders.append(spider)
        return cls(*spiders)

    def _add_spider(self, spider):
        if hasattr(spider, "start_requests"):
            self._start_requests_handlers.append(spider.start_requests)
        if hasattr(spider, "parse"):
            self._parse_handlers.append(spider.parse)

    def parse(self, response, *, middleware=None):
        try:
            if middleware:
                self._handle_input(response, middleware)
            for method in self._parse_handlers:
                res = method(response)
                if middleware:
                    res = self._handle_output(response, res, middleware)
                for r in res:
                    yield r
        except Exception as e:
            try:
                if middleware:
                    self._handle_error(response, e, middleware)
                yield e
            except Exception as _e:
                yield _e

    def start_requests(self, *, middleware=None):
        try:
            for method in self._start_requests_handlers:
                res = method()
                if middleware:
                    res = self._handle_start_requests(res, middleware)
                for r in res:
                    yield r
        except Exception as e:
            yield e

    @staticmethod
    def _handle_input(response, middleware):
        for method in middleware.input_handlers:
            res = method(response)
            if res is not None:
                raise TypeError("Input handler must return None, got {0}".format(type(res)))

    @classmethod
    def _handle_output(cls, response, result, middleware):
        for method in middleware.output_handlers:
            result = method(response, result)
            if not cls._isiterable(result):
                raise TypeError("Response handler must return an iterable object, got {0}".format(type(result)))
        return result

    @staticmethod
    def _handle_error(response, error, middleware):
        for method in middleware.error_handlers:
            res = method(response, error)
            if res is not None:
                raise TypeError("Exception handler must return None, got {0}".format(type(res)))

    @classmethod
    def _handle_start_requests(cls, result, middleware):
        for method in middleware.start_requests_handlers:
            result = method(result)
            if not cls._isiterable(result):
                raise TypeError("Start requests handler must return an iterable object, got {0}".format(type(result)))
        return result

    @staticmethod
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

    @property
    def input_handlers(self):
        return self._input_handlers

    @property
    def output_handlers(self):
        return self._output_handlers

    @property
    def error_handlers(self):
        return self._error_handlers

    @property
    def start_requests_handlers(self):
        return self._start_requests_handlers

    @classmethod
    def _middleware_list_from_config(cls, config):
        mw_list = config.get("spider_middlewares")
        if mw_list:
            if not isinstance(mw_list, list):
                mw_list = [mw_list]
        else:
            mw_list = []
        log.debug("Spider middleware list: {0}".format(mw_list))
        return mw_list
