# coding=utf-8

import time
import logging
import asyncio
from asyncio import Semaphore
from collections import deque
from heapq import heappush, heappop

from . import utils
from . import events

log = logging.getLogger(__name__)


class FifoQueue:
    def __init__(self, dump_dir=None, loop=None):
        self._queue = deque()
        self._dump_dir = dump_dir
        self._loop = loop or asyncio.get_event_loop()
        self._semaphore = Semaphore(0, loop=self._loop)

    def __len__(self):
        return len(self._queue)

    @classmethod
    def from_cluster(cls, cluster):
        queue = cls(dump_dir=utils.get_dump_dir(cluster.config), loop=cluster.loop)
        cluster.event_bus.subscribe(queue.open, events.cluster_start)
        cluster.event_bus.subscribe(queue.close, events.cluster_shutdown)
        return queue

    async def push(self, request):
        self._queue.append(request)
        self._semaphore.release()

    async def pop(self):
        await self._semaphore.acquire()
        return self._queue.popleft()

    def open(self):
        q = utils.load_from_dump_dir('queue', self._dump_dir)
        if q:
            self._queue = q
            self._semaphore = Semaphore(len(self._queue), loop=self._loop)

    def close(self):
        utils.dump_to_dir('queue', self._dump_dir, self._queue)


class LifoQueue(FifoQueue):
    async def pop(self):
        await self._semaphore.acquire()
        return self._queue.pop()


class PriorityQueue:
    def __init__(self, dump_dir=None, loop=None):
        self._queue = []
        self._dump_dir = dump_dir
        self._loop = loop or asyncio.get_event_loop()
        self._semaphore = Semaphore(0, loop=self._loop)

    def __len__(self):
        return len(self._queue)

    @classmethod
    def from_cluster(cls, cluster):
        queue = cls(dump_dir=utils.get_dump_dir(cluster.config), loop=cluster.loop)
        cluster.event_bus.subscribe(queue.open, events.cluster_start)
        cluster.event_bus.subscribe(queue.close, events.cluster_shutdown)
        return queue

    async def push(self, request):
        heappush(self._queue, _PriorityQueueItem(request))
        self._semaphore.release()

    async def pop(self):
        await self._semaphore.acquire()
        item = heappop(self._queue)
        return item.request

    def open(self):
        q = utils.load_from_dump_dir('queue', self._dump_dir)
        if q:
            self._queue = q
            self._semaphore = Semaphore(len(self._queue), loop=self._loop)

    def close(self):
        utils.dump_to_dir('queue', self._dump_dir, self._queue)


class _PriorityQueueItem:
    def __init__(self, request):
        self.request = request
        self.priority = self.request.priority or 0
        self.now = time.time()

    def __cmp__(self, other):
        return utils.cmp((-self.priority, self.now), (-other.priority, other.now))

    def __lt__(self, other):
        return self.__cmp__(other) < 0
