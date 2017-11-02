# coding=utf-8

import logging
import inspect

from .middleware import MiddlewareManager

log = logging.getLogger(__name__)


class ItemPipelineManager(MiddlewareManager):
    def __init__(self, *middlewares):
        self._item_handlers = []
        super().__init__(*middlewares)

    @classmethod
    def _middleware_list_from_cluster(cls, cluster):
        mw_list = cluster.config.get("item_pipelines")
        if mw_list:
            if not isinstance(mw_list, list):
                mw_list = [mw_list]
        else:
            mw_list = []
        log.info("Item pipelines: %s", mw_list)
        return mw_list

    def _add_middleware(self, middleware):
        super()._add_middleware(middleware)
        if hasattr(middleware, "handle_item"):
            self._item_handlers.append(middleware.handle_item)

    async def handle_item(self, item):
        log.debug('Item (%s): %s', type(item).__name__, item)
        for method in self._item_handlers:
            res = method(item)
            if inspect.iscoroutine(res):
                await res
