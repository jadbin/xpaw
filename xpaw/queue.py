# coding=utf-8

import logging
from collections import deque
from asyncio import Semaphore

log = logging.getLogger(__name__)


class RequestQueue:
    async def push(self, request):
        raise NotImplementedError

    async def pop(self):
        raise NotImplementedError


class RequestDequeue(RequestQueue):
    def __init__(self, loop=None):
        self._queue = deque()
        self._semaphore = Semaphore(0, loop=loop)

    @classmethod
    def from_cluster(cls, cluster):
        return cls(loop=cluster.loop)

    async def push(self, request):
        self._queue.append(request)
        self._semaphore.release()

    async def pop(self):
        await self._semaphore.acquire()
        return self._queue.popleft()
