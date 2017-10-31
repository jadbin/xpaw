# coding=utf-8

import asyncio

import pytest
import aiohttp

from xpaw.queue import FifoQueue, LifoQueue, PriorityQueue


class Cluster:
    def __init__(self, loop=None):
        self.loop = loop


async def test_fifo_queue(loop):
    q = FifoQueue.from_cluster(Cluster(loop=loop))
    with pytest.raises(asyncio.TimeoutError):
        with aiohttp.Timeout(0.1, loop=loop):
            await q.pop()
    obj_list = [1, 2, 3]
    for o in obj_list:
        await q.push(o)
    for i in range(len(obj_list)):
        assert await q.pop() == obj_list[i]
    with pytest.raises(asyncio.TimeoutError):
        with aiohttp.Timeout(0.1, loop=loop):
            await q.pop()


async def test_lifo_queue(loop):
    q = LifoQueue.from_cluster(Cluster(loop=loop))
    with pytest.raises(asyncio.TimeoutError):
        with aiohttp.Timeout(0.1, loop=loop):
            await q.pop()
    obj_list = [1, 2, 3]
    for o in obj_list:
        await q.push(o)
    for i in range(len(obj_list)):
        assert await q.pop() == obj_list[len(obj_list) - i - 1]
    with pytest.raises(asyncio.TimeoutError):
        with aiohttp.Timeout(0.1, loop=loop):
            await q.pop()


class PriorityQueueItem:
    def __init__(self, priority):
        self.priority = priority


async def test_priority_queue(loop):
    item1_1 = PriorityQueueItem(1)
    item1_2 = PriorityQueueItem(1)
    item2_1 = PriorityQueueItem(2)
    item2_2 = PriorityQueueItem(2)
    item3_1 = PriorityQueueItem(3)
    item3_2 = PriorityQueueItem(3)
    q = PriorityQueue.from_cluster(Cluster(loop=loop))
    with pytest.raises(asyncio.TimeoutError):
        with aiohttp.Timeout(0.1, loop=loop):
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
        with aiohttp.Timeout(0.1, loop=loop):
            await q.pop()
