# coding=utf-8

import time
import logging
from asyncio import Semaphore
from collections import deque
from heapq import heappush, heappop

from .utils import cmp

log = logging.getLogger(__name__)


class FifoQueue:
    def __init__(self):
        self._queue = deque()
        self._semaphore = Semaphore(0)

    def __len__(self):
        return len(self._queue)

    async def push(self, request):
        self._queue.append(request)
        self._semaphore.release()

    async def pop(self):
        await self._semaphore.acquire()
        return self._queue.popleft()


class LifoQueue(FifoQueue):
    async def pop(self):
        await self._semaphore.acquire()
        return self._queue.pop()


class PriorityQueue:
    def __init__(self):
        self._queue = []
        self._semaphore = Semaphore(0)

    def __len__(self):
        return len(self._queue)

    async def push(self, request):
        heappush(self._queue, _PriorityQueueItem(request))
        self._semaphore.release()

    async def pop(self):
        await self._semaphore.acquire()
        item = heappop(self._queue)
        return item.request


class _PriorityQueueItem:
    def __init__(self, request):
        self.request = request
        self.priority = self.request.priority or 0
        self.now = time.time()

    def __cmp__(self, other):
        return cmp((-self.priority, self.now), (-other.priority, other.now))

    def __lt__(self, other):
        return self.__cmp__(other) < 0
