# coding=utf-8

from os.path import join

import pytest

from xpaw.spider import Spider
from xpaw.cli import main
from xpaw.run import run_crawler, run_spider


def test_run_crawler(tmpdir, capsys):
    proj_name = 'test_run_crawler'
    proj_dir = join(str(tmpdir), proj_name)
    main(argv=['xpaw', 'init', proj_dir])
    run_crawler(proj_dir, downloader_timeout=0.01, log_level='DEBUG')
    _, _ = capsys.readouterr()


def test_run_crawler_bad_config(tmpdir):
    proj_dir = join(str(tmpdir))
    config_file = join(proj_dir, 'config.py')
    with open(config_file, 'w') as f:
        f.write('bad config')
    with pytest.raises(RuntimeError):
        run_crawler(proj_dir, log_level='DEBUG')


def test_failed_to_create_cluster(tmpdir):
    proj_dir = join(str(tmpdir))
    with pytest.raises(Exception):
        run_crawler(proj_dir, log_level='DEBUG')


class DummySpider(Spider):
    def start_requests(self):
        pass

    def parse(self, response):
        pass


def test_supervisor():
    run_spider(DummySpider, downloader_timeout=0.1, log_level='DEBUG')
