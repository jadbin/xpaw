# coding=utf-8

from os.path import join
import logging

import pytest

from xpaw.cli import main
from xpaw.run import run_crawler


def test_run_crawler(tmpdir, capsys):
    proj_name = 'test_run_crawler'
    proj_dir = join(str(tmpdir), proj_name)
    with pytest.raises(FileNotFoundError):
        run_crawler(proj_dir)
    main(argv=['xpaw', 'init', proj_dir])
    run_crawler(proj_dir, downloader_timeout=0.01, log_level='WARNING')
    _, _ = capsys.readouterr()
    logging.getLogger('xpaw').handlers.clear()
