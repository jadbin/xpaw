# coding=utf-8

import pytest
from os.path import join

from xpaw.cmdline import main
from xpaw import __version__


def test_print_help(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(argv=['xpaw'])
    assert excinfo.value.code == 0
    out, _ = capsys.readouterr()
    assert out.startswith('usage:')


def test_unknown_command(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(argv=['xpaw', 'unknown_command'])
    assert excinfo.value.code == 2
    _, _ = capsys.readouterr()


def test_version(capsys):
    main(argv=['xpaw', 'version'])
    out, _ = capsys.readouterr()
    assert out.strip() == 'xpaw version {}'.format(__version__)


spider_source = """# coding=utf-8

from xpaw import Spider


class NewSpider(Spider):

    def start_requests(self):
        pass

    def parse(self, response):
        pass
"""


def test_crawl_spider(tmpdir, capsys):
    spider_file = join(str(tmpdir), 'spider.py')
    with open(spider_file, 'w') as f:
        f.write(spider_source)
    main(argv=['xpaw', 'crawl', spider_file])
    _, _ = capsys.readouterr()


def test_crawl_spider_no_config_file(tmpdir, capsys):
    with pytest.raises(ValueError):
        spider_file = join(str(tmpdir), 'spider.py')
        with open(spider_file, 'w') as f:
            f.write(spider_source)
        main(argv=['xpaw', 'crawl', spider_file,
                   '-c', 'no_such_config.py'])
    _, _ = capsys.readouterr()


def test_crawl_no_spider_file(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(argv=['xpaw', 'crawl', 'dont_exist.py'])
    assert excinfo.value.code == 2
    _, _ = capsys.readouterr()
