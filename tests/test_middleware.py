# coding=utf-8

from xpaw.eventbus import EventBus
from xpaw.config import Config
from xpaw.middleware import MiddlewareManager
from xpaw.errors import NotEnabled


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

    def open(self):
        self.d['enabled_open'] = ''

    def close(self):
        self.d['enabled_close'] = ''


class MyDisabledMiddleware:
    def __init__(self, d):
        self.d = d
        raise NotEnabled

    def open(self):
        self.d['disabled_open'] = ''

    def close(self):
        self.d['disabled_close'] = ''


class Cluster:
    def __init__(self, **kwargs):
        self.event_bus = EventBus()
        self.config = Config(kwargs)


async def test_downloader_middleware_manager_handlers(monkeypatch):
    @classmethod
    def middleware_list_from_cluster(cls, cluster):
        return [lambda data=data: MyMiddleware(data), MyEmptyMiddleware,
                lambda data=data: MyEnabledMiddlewaer(data), lambda data=data: MyDisabledMiddleware(data)]

    monkeypatch.setattr(MiddlewareManager, '_middleware_list_from_cluster', middleware_list_from_cluster)
    data = {}
    middleware_manager = MiddlewareManager.from_cluster(Cluster())
    middleware_manager.open()
    middleware_manager.close()
    assert 'open' in data and 'close' in data
    assert 'enabled_open' in data and 'enabled_close' in data
    assert 'disabled_open' not in data and 'disabled_close' not in data
