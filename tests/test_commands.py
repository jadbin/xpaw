# coding=utf-8

import pytest
from os.path import isfile, isdir, join
from os import remove

from xpaw.cli import main
from xpaw.version import __version__


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
    out, _ = capsys.readouterr()
    assert out.startswith('Unknown command: unknown_command')


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
    with pytest.raises(SystemExit) as excinfo:
        main(argv=['xpaw', 'init', proj_dir])
    assert excinfo.value.code == 1
    main(argv=['xpaw', 'crawl', proj_dir, '-s', 'downloader_timeout=0.01', '-l', 'WARNING'])
    _, _ = capsys.readouterr()
    remove(join(proj_dir, 'config.py'))
    with pytest.raises(SystemExit) as excinfo:
        main(argv=['xpaw', 'init', proj_dir])
    assert excinfo.value.code == 1


def test_init_no_project_dir(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(argv=['xpaw', 'init'])
    assert excinfo.value.code == 2
    _, _ = capsys.readouterr()


def test_crawl_no_spider_file(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(argv=['xpaw', 'crawl', 'dont_exist.py'])
    assert excinfo.value.code == 2
    _, _ = capsys.readouterr()


def test_crawl_no_project_dir(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(argv=['xpaw', 'crawl'])
    assert excinfo.value.code == 2
    _, _ = capsys.readouterr()
