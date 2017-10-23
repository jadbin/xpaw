# coding=utf-8

import os
import sys
import logging
import types

from xpaw.config import Config
from xpaw.utils.project import load_object
from xpaw.downloader import DownloaderMiddlewareManager
from xpaw.spider import SpiderMiddlewareManager

log = logging.getLogger(__name__)


class TaskLoader:
    def __init__(self, proj_dir, base_config=None, **kwargs):
        # add project path
        sys.path.append(proj_dir)
        # copy sys.modules
        modules_keys = set(sys.modules.keys())
        self.config = self._load_task_config(proj_dir, base_config)
        for k, v in kwargs.items():
            self.config.set(k, v, "project")
        self.downloadermw = DownloaderMiddlewareManager.from_config(self.config)
        self.spider = load_object(self.config["spider"])(self.config)
        self.spidermw = SpiderMiddlewareManager.from_config(self.config)
        # recover sys.modules
        keys = list(sys.modules.keys())
        for k in keys:
            if k not in modules_keys:
                del sys.modules[k]
        # remove project path
        sys.path.remove(proj_dir)

    def _load_task_config(self, proj_dir, base_config=None):
        task_config = base_config or Config()
        module = load_object(os.path.join(proj_dir, "config.py"))
        for key in dir(module):
            if not key.startswith("_"):
                value = getattr(module, key)
                if not isinstance(value, (types.FunctionType, types.ModuleType)):
                    task_config.set(key.lower(), value, "project")
        return task_config

    def open_spider(self):
        self.spidermw.open()
        self.downloadermw.open()

    def close_spider(self):
        self.downloadermw.close()
        self.spidermw.close()
