# coding=utf-8

import time
import logging
import asyncio
from asyncio import Semaphore
from collections import deque
from heapq import heappush, heappop
from os.path import join, isfile
import pickle

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

    async def open(self):
        if self._dump_dir:
            file = join(self._dump_dir, 'queue')
            if isfile(file):
                with open(file, 'rb') as f:
                    arr = pickle.load(f)
                for a in arr:
                    r = utils.request_from_dict(a)
                    await self.push(r)

    async def close(self):
        if self._dump_dir:
            reqs = []
            while len(self) > 0:
                r = await self.pop()
                reqs.append(utils.request_to_dict(r))
            with open(join(self._dump_dir, 'queue'), 'wb') as f:
                pickle.dump(reqs, f)


class LifoQueue(FifoQueue):
    async def pop(self):
        await self._semaphore.acquire()
        return self._queue.pop()

    async def open(self):
        if self._dump_dir:
            file = join(self._dump_dir, 'queue')
            if isfile(file):
                with open(file, 'rb') as f:
                    arr = pickle.load(f)
                arr.reverse()
                for a in arr:
                    r = utils.request_from_dict(a)
                    await self.push(r)


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

    async def open(self):
        if self._dump_dir:
            file = join(self._dump_dir, 'queue')
            if isfile(file):
                with open(file, 'rb') as f:
                    arr = pickle.load(f)
                for a in arr:
                    r = utils.request_from_dict(a)
                    await self.push(r)

    async def close(self):
        if self._dump_dir:
            reqs = []
            while len(self) > 0:
                r = await self.pop()
                reqs.append(utils.request_to_dict(r))
            with open(join(self._dump_dir, 'queue'), 'wb') as f:
                pickle.dump(reqs, f)


class _PriorityQueueItem:
    def __init__(self, request):
        self.request = request
        self.priority = self.request.priority or 0
        self.now = time.time()

    def __cmp__(self, other):
        return utils.cmp((-self.priority, self.now), (-other.priority, other.now))

    def __lt__(self, other):
        return self.__cmp__(other) < 0
