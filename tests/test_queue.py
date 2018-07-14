# coding=utf-8

import asyncio

import pytest
import async_timeout

from xpaw.queue import FifoQueue, LifoQueue, PriorityQueue
from xpaw.config import Config
from xpaw.eventbus import EventBus
from xpaw.http import HttpRequest


class Cluster:
    def __init__(self, loop=None, **kwargs):
        self.loop = loop
        self.config = Config(kwargs)
        self.event_bus = EventBus()


async def test_fifo_queue(loop):
    q = FifoQueue.from_cluster(Cluster(loop=loop))
    with pytest.raises(asyncio.TimeoutError):
        with async_timeout.timeout(0.1, loop=loop):
            await q.pop()
    obj_list = [HttpRequest('1'), HttpRequest('2'), HttpRequest('3')]
    for o in obj_list:
        await q.push(o)
    for i in range(len(obj_list)):
        assert await q.pop() == obj_list[i]
    with pytest.raises(asyncio.TimeoutError):
        with async_timeout.timeout(0.1, loop=loop):
            await q.pop()


async def test_fifo_queue_dump(loop, tmpdir):
    q = FifoQueue.from_cluster(Cluster(loop=loop, dump_dir=str(tmpdir)))
    obj_list = [HttpRequest('1'), HttpRequest('2'), HttpRequest('3')]
    for o in obj_list:
        await q.push(o)
    await q.close()
    q2 = FifoQueue.from_cluster(Cluster(loop=loop, dump_dir=str(tmpdir)))
    await q2.open()
    with async_timeout.timeout(0.1, loop=loop):
        for i in range(len(obj_list)):
            assert (await q2.pop()).url == obj_list[i].url


async def test_lifo_queue(loop):
    q = LifoQueue.from_cluster(Cluster(loop=loop))
    with pytest.raises(asyncio.TimeoutError):
        with async_timeout.timeout(0.1, loop=loop):
            await q.pop()
    obj_list = [HttpRequest('1'), HttpRequest('2'), HttpRequest('3')]
    for o in obj_list:
        await q.push(o)
    for i in range(len(obj_list)):
        assert await q.pop() == obj_list[len(obj_list) - i - 1]
    with pytest.raises(asyncio.TimeoutError):
        with async_timeout.timeout(0.1, loop=loop):
            await q.pop()


async def test_lifo_queue_dump(loop, tmpdir):
    q = LifoQueue.from_cluster(Cluster(loop=loop, dump_dir=str(tmpdir)))
    obj_list = [HttpRequest('1'), HttpRequest('2'), HttpRequest('3')]
    for o in obj_list:
        await q.push(o)
    await q.close()
    q2 = LifoQueue.from_cluster(Cluster(loop=loop, dump_dir=str(tmpdir)))
    await q2.open()
    with async_timeout.timeout(0.1, loop=loop):
        for i in range(len(obj_list)):
            assert (await q2.pop()).url == obj_list[len(obj_list) - i - 1].url


async def test_priority_queue(loop):
    item1_1 = HttpRequest('1_1', priority=1)
    item1_2 = HttpRequest('1_2', priority=1)
    item2_1 = HttpRequest('2_1', priority=2)
    item2_2 = HttpRequest('2_2', priority=2)
    item3_1 = HttpRequest('3_1', priority=3)
    item3_2 = HttpRequest('3_2', priority=3)
    q = PriorityQueue.from_cluster(Cluster(loop=loop))
    with pytest.raises(asyncio.TimeoutError):
        with async_timeout.timeout(0.1, loop=loop):
            await q.pop()
    await q.push(item2_1)
    await q.push(item1_1)
    await q.push(item3_1)
    await q.push(item1_2)
    await q.push(item2_2)
    await q.push(item3_2)
    assert await q.pop() is item3_1
    assert await q.pop() is item3_2
    assert await q.pop() is item2_1
    assert await q.pop() is item2_2
    assert await q.pop() is item1_1
    assert await q.pop() is item1_2
    with pytest.raises(asyncio.TimeoutError):
        with async_timeout.timeout(0.1, loop=loop):
            await q.pop()


async def test_priority_queue_dump(loop, tmpdir):
    q = PriorityQueue.from_cluster(Cluster(loop=loop, dump_dir=str(tmpdir)))
    await q.push(HttpRequest('2', priority=2))
    await q.push(HttpRequest('3', priority=3))
    await q.push(HttpRequest('1', priority=1))
    await q.close()
    q2 = PriorityQueue.from_cluster(Cluster(loop=loop, dump_dir=str(tmpdir)))
    await q2.open()
    with async_timeout.timeout(0.1, loop=loop):
        assert (await q2.pop()).url == '3'
        assert (await q2.pop()).url == '2'
        assert (await q2.pop()).url == '1'
