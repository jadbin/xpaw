# coding=utf-8

import pytest

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


async def test_middleware_manager_handlers(monkeypatch):
    @classmethod
    def middleware_list_from_config(cls, config):
        return [lambda data=data: MyMiddleware(data), MyEmptyMiddleware,
                lambda data=data: MyEnabledMiddlewaer(data), lambda data=data: MyDisabledMiddleware(data)]

    monkeypatch.setattr(MiddlewareManager, '_middleware_list_from_config', middleware_list_from_config)
    data = {}
    middleware_manager = MiddlewareManager.from_cluster(Cluster())
    middleware_manager.open()
    middleware_manager.close()
    assert 'open' in data and 'close' in data
    assert 'enabled_open' in data and 'enabled_close' in data
    assert 'disabled_open' not in data and 'disabled_close' not in data


def test_priority_list_from_config():
    d = MiddlewareManager._priority_list_from_config('foo', Cluster().config)
    assert d == {}
    with pytest.raises(AssertionError):
        MiddlewareManager._priority_list_from_config('foo', Cluster(foo='a').config)
    d2 = MiddlewareManager._priority_list_from_config('foo', Cluster(foo=['a', 'b', 'c']).config)
    assert d2['a'] == 0 and d2['b'] == 0 and d2['c'] == 0
    d3 = MiddlewareManager._priority_list_from_config('foo', Cluster(foo=['a', 'b', 'c']).config, shift=0.1)
    assert abs(d3['a'] - 0.1) < 1e-5 and abs(d3['b'] - 0.2) < 1e-5 and abs(d3['c'] - 0.3) < 1e-5
    d4 = MiddlewareManager._priority_list_from_config('foo', Cluster(foo={'a': 2, 'b': 1, 'c': 3}).config, shift=0.1)
    assert d4['a'] == 2 and d4['b'] == 1 and d4['c'] == 3
    d5 = MiddlewareManager._priority_list_from_config('foo', Cluster(foo=['b', 'c', 'b', 'a']).config, shift=0.1)
    assert abs(d5['a'] - 0.3) < 1e-5 and abs(d5['b'] - 0.1) < 1e-5 and abs(d5['c'] - 0.2) < 1e-5


def test_make_component_list():
    d = MiddlewareManager._make_component_list('foo', Cluster(foo=['a', 'c'],
                                                              foo_base={'b': 3, 'd': 100}).config)
    assert d == ['a', 'c', 'b', 'd']
    d2 = MiddlewareManager._make_component_list('foo', Cluster(foo=['a', 'b', 'c'],
                                                               foo_base={'b': 3, 'd': 100}).config)
    assert d2 == ['a', 'b', 'c', 'd']
    d3 = MiddlewareManager._make_component_list('foo', Cluster(foo=['c', 'b', 'a'],
                                                               foo_base=['e', 'd', 'b']).config)
    assert d3 == ['c', 'b', 'a', 'e', 'd']
    d4 = MiddlewareManager._make_component_list('foo', Cluster(foo=['a', 'c', 'b'],
                                                               foo_base=['e', 'd', 'f']).config)
    assert d4 == ['a', 'c', 'b', 'e', 'd', 'f']
    d5 = MiddlewareManager._make_component_list('foo', Cluster(foo={'a': 9, 'c': 1},
                                                               foo_base={'d': 3, 'b': 4}).config)
    assert d5 == ['c', 'd', 'b', 'a']
    d6 = MiddlewareManager._make_component_list('foo', Cluster(foo={'a': 9, 'c': 1, 'b': 2, 'e': None},
                                                               foo_base={'d': 3, 'b': 4, 'e': 8}).config)
    assert d6 == ['c', 'b', 'd', 'a']
    d7 = MiddlewareManager._make_component_list('foo', Cluster(foo={'a': 9, 'c': 1, 'b': 4},
                                                               foo_base={'d': 3, 'b': 2}).config)
    assert d7 == ['c', 'd', 'b', 'a']
    d8 = MiddlewareManager._make_component_list('foo', Cluster(foo={'a': 9, 'c': 1, 'b': 4},
                                                               foo_base=['d', 'b', 'e']).config)
    assert d8 == ['d', 'e', 'c', 'b', 'a']
    d9 = MiddlewareManager._make_component_list('foo', Cluster(foo={'a': 9, 'c': 1},
                                                               foo_base=['d', 'b', 'e']).config)
    assert d9 == ['d', 'b', 'e', 'c', 'a']
    d10 = MiddlewareManager._make_component_list('foo', Cluster(foo={'a': 9, 'c': 1, 'b': None},
                                                                foo_base=['d', 'b', 'e']).config)
    assert d10 == ['d', 'e', 'c', 'a']
