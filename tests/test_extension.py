# coding=utf-8


from xpaw.extension import ExtensionManager
from xpaw.config import Config
from xpaw.eventbus import EventBus
from xpaw import events


class MyExtension:
    def __init__(self, d):
        self.d = d

    def open(self):
        self.d['open'] = ''

    def close(self):
        self.d['close'] = ''


class MyEmptyExtension:
    """
    no method
    """


class Cluster:
    def __init__(self, **kwargs):
        self.event_bus = EventBus()
        self.config = Config(kwargs)


async def test_extension_manager():
    data = {}
    cluster = Cluster(extensions=[lambda d=data: MyExtension(d),
                                  MyEmptyExtension],
                      extensions_base=None,
                      data=data)
    extension = ExtensionManager.from_cluster(cluster)
    await cluster.event_bus.send(events.cluster_start)
    await cluster.event_bus.send(events.cluster_shutdown)
    assert 'open' in data and 'close' in data

    data2 = {}
    cluster2 = Cluster(extensions={lambda d=data2: MyExtension(d): 0},
                       extensions_base=None,
                       data=data2)
    extension2 = ExtensionManager.from_cluster(cluster2)
    await cluster2.event_bus.send(events.cluster_start)
    await cluster2.event_bus.send(events.cluster_shutdown)
    assert 'open' in data2 and 'close' in data2

    cluster3 = Cluster(extensions=None, extensions_base=None, data={})
    ExtensionManager.from_cluster(cluster3)
