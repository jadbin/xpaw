# coding=utf-8

import os
import time
import asyncio
import logging
import threading
from collections import deque

from pykafka import KafkaClient

from xpaw.rpc import RpcServer

log = logging.getLogger(__name__)


class MQCache:
    def __init__(self, rpc_listen, kafka_addr, zookeeper_addr, *, queue_size=100, sleep_time=1):
        self._rpc_listen = rpc_listen
        self._zookeeper_addr = zookeeper_addr
        self._queue_size = queue_size
        self._sleep_time = sleep_time
        self._kafka_client = KafkaClient(hosts=kafka_addr)
        self._mq, self._consumers = {}, {}
        self._set = set()
        self._in_topics = []
        self._out_topics, self._out_index = [], 0
        self._mq_lock, self._in_lock, self._out_lock = threading.Lock(), threading.Lock(), threading.Lock()
        self._loop = asyncio.new_event_loop()
        self._is_running = False

    @classmethod
    def from_config(cls, config):
        kw = {}
        if "mqcache_queue_size" in config:
            kw["queue_size"] = config["mqcache_queue_size"]
        if "mqcache_sleep_time" in config:
            kw["sleep_time"] = config["mqcache_sleep_time"]
        return cls(config.get("mqcache_rpc_listen"),
                   config.get("kafka_addr"),
                   config.get("zookeeper_addr"),
                   **kw)

    def poll(self):
        topic, data = None, None
        with self._out_lock:
            m = len(self._out_topics)
            if m > 0:
                i = self._out_index
                while True:
                    t = self._out_topics[i]
                    with self._mq_lock:
                        mq = self._mq[t]
                        n = len(mq)
                    if n > 0:
                        topic, data = t, mq.popleft()
                        i = 0 if i + 1 >= m else i + 1
                        break
                    i = 0 if i + 1 >= m else i + 1
                    if i == self._out_index:
                        break
                self._out_index = i
        return topic, data

    def start(self):
        if not self._is_running:
            self._is_running = True
            self._start_rpc_server()
            self._start_to_poll()

    def _start_rpc_server(self):
        def _start():
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_forever()
            except Exception:
                log.error("Unexpected error occurred when run loop", exc_info=True)
                raise
            finally:
                self._loop.close()

        server = RpcServer(self._rpc_listen, loop=self._loop)
        server.register_function(self.poll)
        server.serve_forever()
        t = threading.Thread(target=_start)
        t.start()

    def _start_to_poll(self):
        def _poll():
            while self._is_running:
                no_work = True
                try:
                    with self._in_lock:
                        for t in self._in_topics:
                            with self._mq_lock:
                                q = self._mq[t]
                                n, m = len(q), q.maxlen
                            if n < m:
                                msg = self._consumers[t].consume(block=True)
                                if msg:
                                    q.append(msg.value)
                                    no_work = False
                except Exception:
                    log.warning("Unexpected error occurred when poll message", exc_info=True)
                if no_work:
                    time.sleep(self._sleep_time)

        log.info("Start to poll message")
        t = threading.Thread(target=_poll)
        t.start()

    def stop(self):
        if self._is_running:
            self._is_running = False
            if self._loop:
                self._loop.call_soon_threadsafe(self._loop.stop)

    def subscribe(self, topic_set):
        log.info("Subscribe topics: {0}".format(topic_set))
        with self._out_lock:
            with self._in_lock:
                self._in_topics = []
                self._out_topics, self._out_index = [], 0
                for t in topic_set:
                    self._in_topics.append(t)
                    self._out_topics.append(t)
                    if t not in self._set:
                        self._set.add(t)
                        self._load_topic(t)
                del_topic = []
                for t in self._set:
                    if t not in topic_set:
                        del_topic.append(t)
                for t in del_topic:
                    self._set.remove(t)
                    self._remove_topic(t)

    def _load_topic(self, topic):
        q = deque(maxlen=self._queue_size)
        self._mq[topic] = q
        self._consumers[topic] = self._kafka_client.topics[topic.encode("utf-8")].get_balanced_consumer(consumer_group=b"xpaw",
                                                                                                        auto_commit_enable=True,
                                                                                                        zookeeper_connect=self._zookeeper_addr,
                                                                                                        consumer_timeout_ms=10)

    def _remove_topic(self, topic):
        q = self._mq[topic]
        if len(q) > 0:
            producer = None
            try:
                producer = self._kafka_client.topics[topic.encode("utf-8")].get_producer()
                while len(q) > 0:
                    b = q.popleft()
                    producer.produce(b)
            except Exception:
                log.warning("Unexpected error occurred when save the cache of topic '{0}'".format(topic), exc_info=True)
            finally:
                if producer:
                    producer.stop()
        self._mq.pop(topic)
        self._consumers[topic].stop()
        self._consumers.pop(topic)
