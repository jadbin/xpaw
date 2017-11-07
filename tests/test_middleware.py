# coding=utf-8

from xpaw.eventbus import EventBus
from xpaw.config import Config
from xpaw.middleware import MiddlewareManager


class MyMiddleware:
    def __init__(self, d):
        self.d = d

    def open(self):
        self.d['open'] = ''

    def close(self):
        self.d['close'] = ''


class MyEmptyMiddleware:
    """
    no method
    """


class MyEnabledMiddlewaer:
    def __init__(self, d):
        self.d = d
        self.disabled = False

    def open(self):
        self.d['enabled_open'] = ''

    def close(self):
        self.d['enabled_close'] = ''


class MyDisabledMiddleware:
    def __init__(self, d):
        self.d = d
        self.disabled = True

    def open(self):
        self.d['disabled_open'] = ''

    def close(self):
        self.d['disabled_close'] = ''


class Cluster:
    def __init__(self, **kwargs):
        self.event_bus = EventBus()
        self.config = Config(kwargs)


async def test_downloader_middleware_manager_handlers():
    data = {}
    middleware_manager = MiddlewareManager(MyMiddleware(data), MyEmptyMiddleware(),
                                           MyEnabledMiddlewaer(data), MyDisabledMiddleware(data))
    middleware_manager.open()
    middleware_manager.close()
    assert 'open' in data and 'close' in data
    assert 'enabled_open' in data and 'enabled_close' in data
    assert 'disabled_open' not in data and 'disabled_close' not in data
