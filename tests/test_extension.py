# coding=utf-8

import pytest

from xpaw.extension import ExtensionManager
from xpaw.config import Config, DEFAULT_CONFIG
from xpaw.eventbus import EventBus
from xpaw import events


class FooExtension:
    def __init__(self, d):
        self.d = d

    def open(self):
        self.d['open'] = ''

    def close(self):
        self.d['close'] = ''


class DummyExtension:
    """
    no method
    """


class Cluster:
    def __init__(self, **kwargs):
        self.event_bus = EventBus()
        self.config = Config(DEFAULT_CONFIG, **kwargs)


@pytest.mark.asyncio
async def test_extension_manager():
    data = {}
    cluster = Cluster(extensions=[lambda d=data: FooExtension(d),
                                  DummyExtension],
                      default_extensions=None,
                      data=data)
    extensions = ExtensionManager.from_cluster(cluster)
    await cluster.event_bus.send(events.cluster_start)
    await cluster.event_bus.send(events.cluster_shutdown)
    assert 'open' in data and 'close' in data

    cluster3 = Cluster(extensions=None, default_extensions=None, data={})
    ExtensionManager.from_cluster(cluster3)
