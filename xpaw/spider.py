# coding=utf-8

import logging
import inspect
from asyncio import CancelledError

from . import events
from .http import HttpRequest

log = logging.getLogger(__name__)


class Spider:

    @classmethod
    def from_crawler(cls, crawler):
        cls.crawler = crawler
        cls.config = crawler.config
        spider = cls()
        crawler.event_bus.subscribe(spider.open, events.crawler_start)
        crawler.event_bus.subscribe(spider.close, events.crawler_shutdown)
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
            res = self._get_mothod(callback)(response)
        else:
            res = self.parse(response)
        if inspect.iscoroutine(res):
            res = await res
        return res

    async def request_error(self, request, error):
        try:
            if request and request.errback:
                r = self._get_mothod(request.errback)(request, error)
                if inspect.iscoroutine(r):
                    await r
        except CancelledError:
            raise
        except Exception:
            log.warning("Error occurred in the error callback of spider", exc_info=True)

    def _get_mothod(self, method):
        if isinstance(method, str):
            method = getattr(self, method)
        return method


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
