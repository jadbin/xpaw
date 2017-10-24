# coding=utf-8

from os.path import join
import sys
import logging
import types
from configparser import ConfigParser
from importlib import import_module

from xpaw.config import Config
from xpaw.utils.project import load_object
from xpaw.downloader import DownloaderMiddlewareManager
from xpaw.spider import SpiderMiddlewareManager

log = logging.getLogger(__name__)


class TaskLoader:
    def __init__(self, proj_dir, base_config=None, **kwargs):
        # add project path
        sys.path.append(proj_dir)
        self.config = self._load_task_config(proj_dir, base_config)
        for k, v in kwargs.items():
            self.config.set(k, v, "project")
        self.downloadermw = DownloaderMiddlewareManager.from_config(self.config)
        self.spider = load_object(self.config["spider"])(self.config)
        self.spidermw = SpiderMiddlewareManager.from_config(self.config)

    def _load_task_config(self, project_dir, base_config=None):
        task_config = base_config or Config()
        config_parser = ConfigParser()
        config_parser.read(join(project_dir, "setup.cfg"))
        config_path = config_parser.get("config", "default")
        log.debug('Default project configuration: {}'.format(config_path))
        module = import_module(config_path)
        for key in dir(module):
            if not key.startswith("_"):
                value = getattr(module, key)
                if not isinstance(value, (types.FunctionType, types.ModuleType, type)):
                    task_config.set(key.lower(), value, "project")
        return task_config

    def open_spider(self):
        self.spidermw.open()
        self.downloadermw.open()

    def close_spider(self):
        self.downloadermw.close()
        self.spidermw.close()
