# coding=utf-8

import random
from queue import PriorityQueue
from heapq import heappush, heappop

from benchmarks.utils import log_time


class ListHeapPriorityQueue:
    def __init__(self):
        self.q = []

    def push(self, item):
        heappush(self.q, item)

    def pop(self):
        return heappop(self.q)


@log_time('prepare benchmark data')
def prepare_benchmark_data(push_rate=0.5, total=0):
    data = []
    n = 0
    while len(data) + n < total:
        r = random.random()
        if n == 0 or r < push_rate:
            data.append(('push', random.randint(0, 2147483647)))
            n += 1
        else:
            data.append(('pop', None))
            n -= 1
    while n > 0:
        data.append(('pop', None))
        n -= 1
    return data


@log_time('system priority queue')
def benchmark_system_priority_queue(data):
    q = PriorityQueue()
    for d in data:
        op, v = d
        if op == 'push':
            q.put_nowait(v)
        else:
            q.get_nowait()


@log_time('list heap priority queue')
def benchmark_list_heap_priority_queue(data):
    q = ListHeapPriorityQueue()
    for d in data:
        op, v = d
        if op == 'push':
            q.push(v)
        else:
            q.pop()


def main():
    print('--------------------------------')
    print('push rate: 0.6    total: 1000000')
    print('--------------------------------')
    data1 = prepare_benchmark_data(push_rate=0.6, total=1000000)
    benchmark_system_priority_queue(data1)
    benchmark_list_heap_priority_queue(data1)
    print('--------------------------------')
    print('push rate: 0.8    total: 1000000')
    print('--------------------------------')
    data2 = prepare_benchmark_data(push_rate=0.8, total=1000000)
    benchmark_system_priority_queue(data2)
    benchmark_list_heap_priority_queue(data2)


if __name__ == '__main__':
    main()
