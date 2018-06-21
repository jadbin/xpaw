# coding=utf-8

import logging
import os
from os.path import join, isfile
import sys

from .config import BaseConfig, Config
from .cluster import LocalCluster
from . import utils

log = logging.getLogger(__name__)


def run_crawler(proj_dir, **kwargs):
    config = BaseConfig(kwargs)
    run_cluster(proj_dir=proj_dir, base_config=config)


def run_spider(spider, **kwargs):
    config = BaseConfig(kwargs)
    config.set("spider", spider)
    run_cluster(base_config=config)


def run_cluster(proj_dir=None, base_config=None):
    config = _load_task_config(proj_dir=proj_dir, base_config=base_config)
    utils.configure_logger('xpaw', config)
    if config.getbool('daemon'):
        utils.be_daemon()
    pid_file = config.get('pid_file')
    if pid_file is not None:
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))
    try:
        cluster = LocalCluster(config)
    except Exception:
        log.error('Fatal error occurred when creating cluster', exc_info=True)
        _remove_pid_file(pid_file)
        raise
    try:
        cluster.start()
    finally:
        _remove_pid_file(pid_file)
        cluster.close()
    utils.remove_logger('xpaw')


def _load_task_config(proj_dir=None, base_config=None):
    if proj_dir is not None and proj_dir not in sys.path:
        # add project path
        sys.path.append(proj_dir)
    task_config = Config()
    if proj_dir is not None:
        config_file = join(proj_dir, 'config.py')
        if isfile(config_file):
            try:
                c = utils.load_config(config_file)
            except Exception:
                raise RuntimeError('Cannot read the configuration file {}'.format(config_file))
            for k, v in utils.iter_settings(c):
                task_config.set(k, v)
    task_config.update(base_config)
    return task_config


def _remove_pid_file(pid_file):
    if pid_file is not None:
        try:
            os.remove(pid_file)
        except Exception:
            pass
