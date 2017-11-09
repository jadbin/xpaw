# coding=utf-8

import logging

from .middleware import MiddlewareManager

log = logging.getLogger(__name__)


class ExtensionManager(MiddlewareManager):
    @classmethod
    def _middleware_list_from_config(cls, config):
        return cls._make_component_list('extensions', config)
