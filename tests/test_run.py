# coding=utf-8

from os.path import join

import pytest

from xpaw.spider import Spider
from xpaw.run import run_spider, run_spider_project, make_requests
from xpaw.http import HttpRequest, HttpResponse
from xpaw.errors import ClientError, HttpError

spider_source = """# coding=utf-8

from xpaw import Spider


class NewSpider(Spider):

    def start_requests(self):
        pass

    def parse(self, response):
        pass
"""

config_source = """# coding=utf-8

spider = 'spider.NewSpider'
"""


def test_run_spider_project(tmpdir):
    proj_dir = str(tmpdir)
    spider_file = join(proj_dir, 'spider.py')
    config_file = join(proj_dir, 'config.py')
    with open(spider_file, 'w') as f:
        f.write(spider_source)
    with open(config_file, 'w') as f:
        f.write(config_source)
    run_spider_project(proj_dir, log_level='DEBUG')


def test_run_spider_project_with_bad_config(tmpdir, capsys):
    proj_dir = join(str(tmpdir))
    config_file = join(proj_dir, 'config.py')
    with open(config_file, 'w') as f:
        f.write('bad config')
    with pytest.raises(SyntaxError):
        run_spider_project(proj_dir, log_level='DEBUG')
    _, _ = capsys.readouterr()


def test_failed_to_create_crawler(tmpdir, capsys):
    proj_dir = join(str(tmpdir))
    with pytest.raises(Exception):
        run_spider_project(proj_dir, log_level='DEBUG')
    _, _ = capsys.readouterr()


class DummySpider(Spider):
    def start_requests(self):
        pass

    def parse(self, response):
        pass


def test_run_spider():
    run_spider(DummySpider, log_level='DEBUG')


def test_make_requests():
    requests = [None, 'http://unknonw',
                'http://python.org/', HttpRequest('http://python.org'),
                'http://httpbin.org/status/404']
    results = make_requests(requests, log_level='DEBUG')
    assert len(results) == len(requests)
    assert results[0] is None
    assert isinstance(results[1], ClientError)
    assert isinstance(results[2], HttpResponse) and results[2].status == 200
    assert isinstance(results[3], HttpResponse) and results[3].status == 200
    assert isinstance(results[4], HttpError) and results[4].response.status == 404
