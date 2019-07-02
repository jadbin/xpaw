# coding=utf-8

import asyncio

import pytest
import async_timeout

from xpaw.queue import FifoQueue, LifoQueue, PriorityQueue
from xpaw.http import HttpRequest


@pytest.mark.asyncio
async def test_fifo_queue():
    q = FifoQueue()
    with pytest.raises(asyncio.TimeoutError):
        with async_timeout.timeout(0.1):
            await q.pop()
    obj_list = [HttpRequest('1'), HttpRequest('2'), HttpRequest('3')]
    for o in obj_list:
        await q.push(o)
    for i in range(len(obj_list)):
        assert await q.pop() == obj_list[i]
    with pytest.raises(asyncio.TimeoutError):
        with async_timeout.timeout(0.1):
            await q.pop()


@pytest.mark.asyncio
async def test_lifo_queue():
    q = LifoQueue()
    with pytest.raises(asyncio.TimeoutError):
        with async_timeout.timeout(0.1):
            await q.pop()
    obj_list = [HttpRequest('1'), HttpRequest('2'), HttpRequest('3')]
    for o in obj_list:
        await q.push(o)
    for i in range(len(obj_list)):
        assert await q.pop() == obj_list[len(obj_list) - i - 1]
    with pytest.raises(asyncio.TimeoutError):
        with async_timeout.timeout(0.1):
            await q.pop()


@pytest.mark.asyncio
async def test_priority_queue():
    item1_1 = HttpRequest('1_1', priority=1)
    item1_2 = HttpRequest('1_2', priority=1)
    item2_1 = HttpRequest('2_1', priority=2)
    item2_2 = HttpRequest('2_2', priority=2)
    item3_1 = HttpRequest('3_1', priority=3)
    item3_2 = HttpRequest('3_2', priority=3)
    q = PriorityQueue()
    with pytest.raises(asyncio.TimeoutError):
        with async_timeout.timeout(0.1):
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
        with async_timeout.timeout(0.1):
            await q.pop()
