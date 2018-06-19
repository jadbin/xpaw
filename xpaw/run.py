# coding=utf-8

from os.path import isfile, join, abspath

from .config import Config
from .cluster import LocalCluster
from . import utils


def run_crawler(project_dir, **kwargs):
    if not isfile(join(project_dir, "setup.cfg")):
        raise FileNotFoundError("Cannot find 'setup.cfg' in {}".format(abspath(project_dir)))

    config = Config(kwargs)
    log_hanlder = utils.configure_logging("xpaw", config)
    try:
        cluster = LocalCluster(project_dir, config)
        cluster.start()
        cluster.close()
    finally:
        utils.remove_logger('xpaw', log_hanlder)


def run_spider(spider, **kwargs):
    config = Config(kwargs)
    config.set("spider", spider)
    log_handler = utils.configure_logging("xpaw", config)
    try:
        cluster = LocalCluster(None, config)
        cluster.start()
        cluster.close()
    finally:
        utils.remove_logger('xpaw', log_handler)
