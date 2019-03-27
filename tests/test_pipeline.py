# coding=utf-8

import pytest

from xpaw.pipeline import ItemPipelineManager
from xpaw import events
from .crawler import Crawler


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
    def from_crawler(cls, crawler):
        return cls(crawler.config['data'])

    @pytest.mark.asyncio
    async def handle_item(self, item):
        self.d['async_handle_item'] = item


@pytest.mark.asyncio
async def test_item_pipeline_manager():
    data = {}
    crawler = Crawler(item_pipelines=[lambda d=data: FooItemPipeline(d),
                                      DummyItemPipeline,
                                      FooAsyncItemPipeline],
                      default_item_pipelines=None,
                      data=data)
    pipeline = ItemPipelineManager.from_crawler(crawler)
    obj = object()
    await crawler.event_bus.send(events.crawler_start)
    await pipeline.handle_item(obj)
    await crawler.event_bus.send(events.crawler_shutdown)
    assert 'open' in data and 'close' in data
    assert data['handle_item'] is obj and data['async_handle_item'] is obj

    crawler3 = Crawler(item_pipelines=None, default_item_pipelines=None, data={})
    ItemPipelineManager.from_crawler(crawler3)
