# coding=utf-8

import logging

from xpaw.utils.project import load_object

log = logging.getLogger(__name__)


class MiddlewareManager:
    def __init__(self, *middlewares):
        for middleware in middlewares:
            self._add_middleware(middleware)

    @classmethod
    def _middleware_list_from_config(cls, config):
        raise NotImplementedError

    @classmethod
    def from_config(cls, config):
        mw_list = cls._middleware_list_from_config(config)
        mws = []
        for cls_path in mw_list:
            mw_cls = load_object(cls_path)
            if hasattr(mw_cls, "from_config"):
                mw = mw_cls.from_config(config)
            else:
                mw = mw_cls()
            mws.append(mw)
        return cls(*mws)

    def _add_middleware(self, middleware):
        raise NotImplementedError
