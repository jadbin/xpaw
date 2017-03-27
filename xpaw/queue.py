# coding=utf-8

from collections import deque


class RequestQueue:
    def push(self, request):
        raise NotImplementedError

    def pop(self):
        raise NotImplementedError


class RequestDequeue(RequestQueue):
    def __init__(self):
        self._queue = deque()

    def push(self, request):
        self._queue.append(request)

    def pop(self):
        if len(self._queue) > 0:
            return self._queue.popleft()
