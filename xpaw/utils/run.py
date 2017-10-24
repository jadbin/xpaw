# coding=utf-8

from os.path import isfile, join, abspath

from xpaw.utils.log import configure_logging
from xpaw.config import Config
from xpaw.cluster import LocalCluster


def run_crawler(project_dir, **kwargs):
    if not isfile(join(project_dir, "setup.cfg")):
        raise FileNotFoundError("Connot find 'setup.cfg' in {}".format(abspath(project_dir)))

    config = Config(kwargs, priority="project")
    configure_logging("xpaw", config)
    cluster = LocalCluster(project_dir, config)
    cluster.start()
