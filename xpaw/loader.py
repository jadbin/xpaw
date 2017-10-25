# coding=utf-8

from os.path import join
import sys
import logging
import types
from configparser import ConfigParser
from importlib import import_module

from xpaw.config import Config
from xpaw.utils import load_object
from xpaw.downloader import DownloaderMiddlewareManager
from xpaw.spider import SpiderMiddlewareManager

log = logging.getLogger(__name__)


class TaskLoader:
    def __init__(self, proj_dir=None, base_config=None, **kwargs):
        if proj_dir is not None:
            # add project path
            sys.path.append(proj_dir)
        self.config = self._load_task_config(proj_dir, base_config)
        for k, v in kwargs.items():
            self.config.set(k, v, "project")
        self.spider = load_object(self.config["spider"])(self.config)
        log.debug("Spider: {}".format(".".join((type(self.spider).__module__,
                                                type(self.spider).__name__))))
        self.downloadermw = DownloaderMiddlewareManager.from_config(self.config)
        self.spidermw = SpiderMiddlewareManager.from_config(self.config)

    def _load_task_config(self, project_dir=None, base_config=None):
        task_config = base_config or Config()
        if project_dir is not None:
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
