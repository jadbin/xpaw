# coding=utf-8

from os.path import isfile, join, abspath

from .config import Config
from .cluster import LocalCluster
from .utils import configure_logging


def run_crawler(project_dir, **kwargs):
    if not isfile(join(project_dir, "setup.cfg")):
        raise FileNotFoundError("Cannot find 'setup.cfg' in {}".format(abspath(project_dir)))

    config = Config(kwargs)
    configure_logging("xpaw", config)
    cluster = LocalCluster(project_dir, config)
    cluster.start()


def run_spider(spider, **kwargs):
    config = Config(kwargs)
    config.set("spider", spider)
    configure_logging("xpaw", config)
    cluster = LocalCluster(None, config)
    cluster.start()
