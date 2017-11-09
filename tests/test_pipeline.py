# coding=utf-8

from xpaw.pipeline import ItemPipelineManager
from xpaw.config import Config
from xpaw.eventbus import EventBus
from xpaw import events


class MyItemPipeline:
    def __init__(self, d):
        self.d = d

    def handle_item(self, item):
        self.d['handle_item'] = item

    def open(self):
        self.d['open'] = ''

    def close(self):
        self.d['close'] = ''


class MyEmptyItemPipeline:
    """
    no method
    """


class MyAsyncItemPipeline(MyItemPipeline):
    @classmethod
    def from_cluster(cls, cluster):
        return cls(cluster.config['data'])

    async def handle_item(self, item):
        self.d['async_handle_item'] = item


class Cluster:
    def __init__(self, **kwargs):
        self.event_bus = EventBus()
        self.config = Config(kwargs)


async def test_item_pipeline_manager():
    data = {}
    cluster = Cluster(item_pipelines=[lambda d=data: MyItemPipeline(d),
                                      MyEmptyItemPipeline,
                                      MyAsyncItemPipeline],
                      item_pipelines_base=None,
                      data=data)
    pipeline = ItemPipelineManager.from_cluster(cluster)
    obj = object()
    await cluster.event_bus.send(events.cluster_start)
    await pipeline.handle_item(obj)
    await cluster.event_bus.send(events.cluster_shutdown)
    assert 'open' in data and 'close' in data
    assert data['handle_item'] is obj and data['async_handle_item'] is obj

    data2 = {}
    cluster2 = Cluster(item_pipelines={lambda d=data2: MyItemPipeline(d): 0},
                       item_pipelines_base=None,
                       data=data2)
    pipeline2 = ItemPipelineManager.from_cluster(cluster2)
    obj2 = object()
    await cluster2.event_bus.send(events.cluster_start)
    await pipeline2.handle_item(obj2)
    await cluster2.event_bus.send(events.cluster_shutdown)
    assert 'open' in data2 and 'close' in data2
    assert data2['handle_item'] is obj2

    cluster3 = Cluster(item_pipelines=None, item_pipelines_base=None, data={})
    ItemPipelineManager.from_cluster(cluster3)
