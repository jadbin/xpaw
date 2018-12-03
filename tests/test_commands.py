# coding=utf-8

import pytest
from os.path import isfile, isdir, join
from os import remove

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


def test_init(tmpdir, capsys):
    proj_name = 'init_test'
    proj_dir = join(str(tmpdir), proj_name)
    main(argv=['xpaw', 'init', proj_dir])
    assert isdir(join(proj_dir))
    assert isfile(join(proj_dir, 'config.py'))
    assert isdir(join(proj_dir, proj_name))
    assert isfile(join(proj_dir, proj_name, '__init__.py'))
    assert isfile(join(proj_dir, proj_name, 'items.py'))
    assert isfile(join(proj_dir, proj_name, 'pipelines.py'))
    assert isfile(join(proj_dir, proj_name, 'spider.py'))
    main(argv=['xpaw', 'crawl', proj_dir, '-l', 'WARNING'])
    _, _ = capsys.readouterr()
    remove(join(proj_dir, 'config.py'))


def test_init_no_project_dir(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(argv=['xpaw', 'init'])
    assert excinfo.value.code == 2
    _, _ = capsys.readouterr()


def test_crawl_project(tmpdir, capsys):
    proj_name = 'test_crawl_project'
    proj_dir = join(str(tmpdir), proj_name)
    main(argv=['xpaw', 'init', proj_dir])
    main(argv=['xpaw', 'crawl', proj_dir])
    _, _ = capsys.readouterr()


def test_crawl_no_project_dir(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(argv=['xpaw', 'crawl'])
    assert excinfo.value.code == 2
    _, _ = capsys.readouterr()


def test_crawl_spider(tmpdir, capsys):
    proj_name = 'test_crawl_spider'
    proj_dir = join(str(tmpdir), proj_name)
    main(argv=['xpaw', 'init', proj_dir])
    main(argv=['xpaw', 'crawl', join(proj_dir, proj_name, 'spider.py')])
    _, _ = capsys.readouterr()


def test_crawl_spider_no_config_file(tmpdir, capsys):
    proj_name = 'test_crawl_spider'
    proj_dir = join(str(tmpdir), proj_name)
    main(argv=['xpaw', 'init', proj_dir])
    with pytest.raises(ValueError):
        main(argv=['xpaw', 'crawl', join(proj_dir, proj_name, 'spider.py'),
                   '-c', 'no_such_config.py'])
    _, _ = capsys.readouterr()


def test_crawl_no_spider_file(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(argv=['xpaw', 'crawl', 'dont_exist.py'])
    assert excinfo.value.code == 2
    _, _ = capsys.readouterr()
