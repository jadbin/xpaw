# coding=utf-8

import pytest

from xpaw.eventbus import EventBus
from xpaw.config import Config
from xpaw.middleware import MiddlewareManager
from xpaw.errors import NotEnabled


class FooMiddleware:
    def __init__(self, d):
        self.d = d

    def open(self):
        self.d['open'] = ''

    def close(self):
        self.d['close'] = ''


class DummyMiddleware:
    """
    no method
    """


class FooEnabledMiddleware:
    def __init__(self, d):
        self.d = d

    def open(self):
        self.d['enabled_open'] = ''

    def close(self):
        self.d['enabled_close'] = ''


class FooDisabledMiddleware:
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


async def test_middleware_manager_handlers(monkeypatch):
    @classmethod
    def middleware_list_from_config(cls, config):
        return [lambda data=data: FooMiddleware(data), DummyMiddleware,
                lambda data=data: FooEnabledMiddleware(data), lambda data=data: FooDisabledMiddleware(data)]

    monkeypatch.setattr(MiddlewareManager, '_middleware_list_from_config', middleware_list_from_config)
    data = {}
    middleware_manager = MiddlewareManager.from_cluster(Cluster())
    middleware_manager.open()
    middleware_manager.close()
    assert 'open' in data and 'close' in data
    assert 'enabled_open' in data and 'enabled_close' in data
    assert 'disabled_open' not in data and 'disabled_close' not in data


def test_priority_list_from_config():
    cls = MiddlewareManager._priority_list_from_config
    d = cls('foo', Cluster().config)
    assert d == {}
    with pytest.raises(AssertionError):
        cls('foo', Cluster(foo='a').config)
    d2 = cls('foo', Cluster(foo=['a', 'b', 'c']).config)
    assert d2['a'] == (0, 0) and d2['b'] == (0, 1) and d2['c'] == (0, 2)
    d3 = cls('foo', Cluster(foo={'a': 2, 'b': 1, 'c': 3}).config)
    assert d3['a'] == (2,) and d3['b'] == (1,) and d3['c'] == (3,)


def test_make_component_list():
    cls = MiddlewareManager._make_component_list
    d = cls('foo', Cluster(foo=['a', 'c'], foo_base={'b': 3, 'd': 100}).config)
    assert d == ['a', 'c', 'b', 'd']
    d2 = cls('foo', Cluster(foo=['a', 'b', 'c'], foo_base={'b': 3, 'd': 100}).config)
    assert d2 == ['a', 'b', 'c', 'd']
    d3 = cls('foo', Cluster(foo={'a': 9, 'c': 1}, foo_base={'d': 3, 'b': 4}).config)
    assert d3 == ['c', 'd', 'b', 'a']
    d4 = cls('foo', Cluster(foo={'a': 9, 'c': 1, 'b': 4}, foo_base={'d': 3, 'b': 2}).config)
    assert d4 == ['c', 'd', 'b', 'a']
