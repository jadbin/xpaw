# coding=utf-8

import asyncio

import pytest
import async_timeout

from xpaw.queue import FifoQueue, LifoQueue, PriorityQueue
from xpaw.http import HttpRequest
from .crawler import Crawler


@pytest.mark.asyncio
async def test_fifo_queue():
    q = FifoQueue.from_crawler(Crawler())
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
async def test_fifo_queue_dump(tmpdir):
    q = FifoQueue.from_crawler(Crawler(dump_dir=str(tmpdir)))
    obj_list = [HttpRequest('1'), HttpRequest('2'), HttpRequest('3')]
    for o in obj_list:
        await q.push(o)
    await q.close()
    q2 = FifoQueue.from_crawler(Crawler(dump_dir=str(tmpdir)))
    await q2.open()
    with async_timeout.timeout(0.1):
        for i in range(len(obj_list)):
            assert (await q2.pop()).url == obj_list[i].url


@pytest.mark.asyncio
async def test_lifo_queue():
    q = LifoQueue.from_crawler(Crawler())
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
async def test_lifo_queue_dump(tmpdir):
    q = LifoQueue.from_crawler(Crawler(dump_dir=str(tmpdir)))
    obj_list = [HttpRequest('1'), HttpRequest('2'), HttpRequest('3')]
    for o in obj_list:
        await q.push(o)
    await q.close()
    q2 = LifoQueue.from_crawler(Crawler(dump_dir=str(tmpdir)))
    await q2.open()
    with async_timeout.timeout(0.1):
        for i in range(len(obj_list)):
            assert (await q2.pop()).url == obj_list[len(obj_list) - i - 1].url


@pytest.mark.asyncio
async def test_priority_queue():
    item1_1 = HttpRequest('1_1', priority=1)
    item1_2 = HttpRequest('1_2', priority=1)
    item2_1 = HttpRequest('2_1', priority=2)
    item2_2 = HttpRequest('2_2', priority=2)
    item3_1 = HttpRequest('3_1', priority=3)
    item3_2 = HttpRequest('3_2', priority=3)
    q = PriorityQueue.from_crawler(Crawler())
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


@pytest.mark.asyncio
async def test_priority_queue_dump(tmpdir):
    q = PriorityQueue.from_crawler(Crawler(dump_dir=str(tmpdir)))
    await q.push(HttpRequest('2', priority=2))
    await q.push(HttpRequest('3', priority=3))
    await q.push(HttpRequest('1', priority=1))
    await q.close()
    q2 = PriorityQueue.from_crawler(Crawler(dump_dir=str(tmpdir)))
    await q2.open()
    with async_timeout.timeout(0.1):
        assert (await q2.pop()).url == 'http://3'
        assert (await q2.pop()).url == 'http://2'
        assert (await q2.pop()).url == 'http://1'
