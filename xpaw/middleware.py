# coding=utf-8

import logging

from .utils import load_object
from . import events

log = logging.getLogger(__name__)


class MiddlewareManager:
    def __init__(self, *middlewares):
        self._open_handlers = []
        self._close_handlers = []
        for middleware in middlewares:
            self._add_middleware(middleware)

    @classmethod
    def _middleware_list_from_cluster(cls, cluster):
        raise NotImplementedError

    @classmethod
    def from_cluster(cls, cluster):
        mw_list = cls._middleware_list_from_cluster(cluster)
        mws = []
        for cls_path in mw_list:
            mw_cls = load_object(cls_path)
            if hasattr(mw_cls, "from_cluster"):
                mw = mw_cls.from_cluster(cluster)
            else:
                mw = mw_cls()
            mws.append(mw)
        mwm = cls(*mws)
        cluster.event_bus.subscribe(mwm.open, events.cluster_start)
        cluster.event_bus.subscribe(mwm.close, events.cluster_shutdown)
        return mwm

    def _add_middleware(self, middleware):
        if hasattr(middleware, "open"):
            self._open_handlers.append(middleware.open)
        if hasattr(middleware, "close"):
            self._close_handlers.insert(0, middleware.close)

    def open(self):
        for method in self._open_handlers:
            method()

    def close(self):
        for method in self._close_handlers:
            method()
