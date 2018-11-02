# coding=utf-8

import pytest

from xpaw.pipeline import ItemPipelineManager
from xpaw.config import Config, DEFAULT_CONFIG
from xpaw.eventbus import EventBus
from xpaw import events


class FooItemPipeline:
    def __init__(self, d):
        self.d = d

    def handle_item(self, item):
        self.d['handle_item'] = item

    def open(self):
        self.d['open'] = ''

    def close(self):
        self.d['close'] = ''


class DummyItemPipeline:
    """
    no method
    """


class FooAsyncItemPipeline(FooItemPipeline):
    @classmethod
    def from_cluster(cls, cluster):
        return cls(cluster.config['data'])

    @pytest.mark.asyncio
    async def handle_item(self, item):
        self.d['async_handle_item'] = item


class Cluster:
    def __init__(self, **kwargs):
        self.event_bus = EventBus()
        self.config = Config(DEFAULT_CONFIG, **kwargs)


@pytest.mark.asyncio
async def test_item_pipeline_manager():
    data = {}
    cluster = Cluster(item_pipelines=[lambda d=data: FooItemPipeline(d),
                                      DummyItemPipeline,
                                      FooAsyncItemPipeline],
                      default_item_pipelines=None,
                      data=data)
    pipeline = ItemPipelineManager.from_cluster(cluster)
    obj = object()
    await cluster.event_bus.send(events.cluster_start)
    await pipeline.handle_item(obj)
    await cluster.event_bus.send(events.cluster_shutdown)
    assert 'open' in data and 'close' in data
    assert data['handle_item'] is obj and data['async_handle_item'] is obj

    cluster3 = Cluster(item_pipelines=None, default_item_pipelines=None, data={})
    ItemPipelineManager.from_cluster(cluster3)
