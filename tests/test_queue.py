# coding=utf-8

import asyncio

import pytest
import async_timeout

from xpaw.queue import RequestDequeue


class Cluster:
    def __init__(self, loop=None):
        self.loop = loop


async def test_request_queue(loop):
    q = RequestDequeue.from_cluster(Cluster(loop=loop))
    q.open()
    with pytest.raises(asyncio.TimeoutError):
        with async_timeout.timeout(0.1):
            await q.pop()
    obj_list = [1, 2, 3]
    for o in obj_list:
        await q.push(o)
    for i in range(len(obj_list)):
        assert await q.pop() == obj_list[i]
    with pytest.raises(asyncio.TimeoutError):
        with async_timeout.timeout(0.1):
            await q.pop()
    q.close()
