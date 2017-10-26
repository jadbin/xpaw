# coding=utf-8

import pytest

from xpaw.handler import every


def test_every_value_error():
    with pytest.raises(ValueError):
        @every()
        def func():
            pass


def test_every():
    @every(hours=1)
    def func_hours():
        pass

    assert func_hours.cron_job is True and func_hours.cron_tick == 3600

    @every(minutes=1)
    def func_minutes():
        pass

    assert func_minutes.cron_job is True and func_minutes.cron_tick == 60

    @every(seconds=1)
    def func_seconds():
        pass

    assert func_seconds.cron_job is True and func_seconds.cron_tick == 1

    @every(hours=1, minutes=1, seconds=1)
    def func():
        pass

    assert func.cron_job is True and func.cron_tick == 3661
