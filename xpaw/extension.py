# coding=utf-8

import logging

from .middleware import MiddlewareManager

log = logging.getLogger(__name__)


class ExtensionManager(MiddlewareManager):
    @classmethod
    def _middleware_list_from_cluster(cls, cluster):
        mw_list = cluster.config.get("extensions")
        if mw_list:
            if not isinstance(mw_list, list):
                mw_list = [mw_list]
        else:
            mw_list = []
        log.info("Extensions: %s", mw_list)
        return mw_list
