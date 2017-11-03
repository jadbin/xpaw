# coding=utf-8

import pytest
import logging
from os.path import isfile, isdir, join

from xpaw.cli import main
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
    assert isfile(join(proj_dir, 'setup.cfg'))
    assert isdir(join(proj_dir, proj_name))
    assert isfile(join(proj_dir, proj_name, '__init__.py'))
    assert isfile(join(proj_dir, proj_name, 'config.py'))
    assert isfile(join(proj_dir, proj_name, 'items.py'))
    assert isfile(join(proj_dir, proj_name, 'pipelines.py'))
    assert isfile(join(proj_dir, proj_name, 'spider.py'))
    with pytest.raises(SystemExit) as excinfo:
        main(argv=['xpaw', 'init', proj_dir])
    assert excinfo.value.code == 1
    main(argv=['xpaw', 'crawl', proj_dir, '-s', 'downloader_timeout=0.01', '-l', 'WARNING'])
    _, _ = capsys.readouterr()
    logging.getLogger('xpaw').handlers.clear()



def test_init_no_project_dir(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(argv=['xpaw', 'init'])
    assert excinfo.value.code == 2
    _, _ = capsys.readouterr()


def test_error_usage_of_set_argument(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(argv=['xpaw', 'version', '-s', 'wrong'])
    assert excinfo.value.code == 2
    _, _ = capsys.readouterr()


def test_crawl_no_project_dir(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(argv=['xpaw', 'crawl'])
    assert excinfo.value.code == 2
    _, _ = capsys.readouterr()


def test_crawl_no_setup_cfg(tmpdir, capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(argv=['xpaw', 'crawl', str(tmpdir)])
    assert excinfo.value.code == 1
    _, _ = capsys.readouterr()
