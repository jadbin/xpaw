# coding=utf-8

from .config import Config
from .cluster import LocalCluster


def run_crawler(proj_dir, **kwargs):
    config = Config(kwargs)
    run_cluster(proj_dir=proj_dir, config=config)


def run_spider(spider, **kwargs):
    config = Config(kwargs)
    config.set("spider", spider)
    run_cluster(config=config)


def run_cluster(proj_dir=None, config=None):
    cluster = LocalCluster(proj_dir=proj_dir, config=config)
    try:
        cluster.start()
    finally:
        cluster.close()
