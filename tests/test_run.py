# coding=utf-8

from os.path import join

import pytest

from xpaw.spider import Spider
from xpaw.cli import main
from xpaw.run import run_crawler, run_spider, make_requests
from xpaw.http import HttpRequest, HttpResponse
from xpaw.errors import IgnoreRequest


def test_run_crawler(tmpdir):
    proj_name = 'test_run_crawler'
    proj_dir = join(str(tmpdir), proj_name)
    main(argv=['xpaw', 'init', proj_dir])
    run_crawler(proj_dir, downloader_timeout=0.01, log_level='DEBUG')


def test_run_crawler_bad_config(tmpdir, capsys):
    proj_dir = join(str(tmpdir))
    config_file = join(proj_dir, 'config.py')
    with open(config_file, 'w') as f:
        f.write('bad config')
    with pytest.raises(RuntimeError):
        run_crawler(proj_dir, log_level='DEBUG')
    _, _ = capsys.readouterr()


def test_failed_to_create_cluster(tmpdir, capsys):
    proj_dir = join(str(tmpdir))
    with pytest.raises(Exception):
        run_crawler(proj_dir, log_level='DEBUG')
    _, _ = capsys.readouterr()


class DummySpider(Spider):
    def start_requests(self):
        pass

    def parse(self, response):
        pass


def test_run_spider():
    run_spider(DummySpider, downloader_timeout=0.1, log_level='DEBUG')


def test_make_requests():
    requests = [None, 'http://localhost:80', 'http://python.org/', HttpRequest('http://python.org')]
    results = make_requests(requests)
    assert len(results) == len(requests)
    assert results[0] is None
    assert isinstance(results[1], IgnoreRequest)
    assert isinstance(results[2], HttpResponse) and results[2].status == 200
    assert isinstance(results[3], HttpResponse) and results[3].status == 200
