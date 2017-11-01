# coding=utf-8

from xpaw.pipeline import ItemPipelineManager
from xpaw.config import Config
from xpaw.eventbus import EventBus


class MyItemPipeline:
    def __init__(self, d):
        self.d = d

    def handle_item(self, item):
        self.d['func'] = item


class MyAsyncItemPipeline(MyItemPipeline):
    @classmethod
    def from_cluster(cls, cluster):
        return cls(cluster.config['data'])

    async def handle_item(self, item):
        self.d['async'] = item


class Cluster:
    def __init__(self, **kwargs):
        self.event_bus = EventBus()
        self.config = Config(kwargs)


async def test_item_pipeline():
    data = {}
    cluster = Cluster(item_pipelines=[lambda d=data: MyItemPipeline(d),
                                      MyAsyncItemPipeline],
                      data=data)
    pipeline = ItemPipelineManager.from_cluster(cluster)
    obj = object()
    await pipeline.handle_item(obj)
    assert data['func'] is obj and data['async'] is obj

    cluster2 = Cluster(item_pipelines=lambda d=data: MyItemPipeline(d),
                       data=data)
    pipeline2 = ItemPipelineManager.from_cluster(cluster2)
    obj2 = object()
    await pipeline2.handle_item(obj2)
    assert data['func'] is obj2

    cluster3 = Cluster(item_pipelines=None, data=data)
    ItemPipelineManager.from_cluster(cluster3)
