# coding=utf-8

import os
import time
import pytest

from xpaw import mqcache
from xpaw.mqcache import MQCache
from xpaw.rpc import RpcClient

from .helpers import wait_server_start


class TopicClient:
    class TopicDict:
        class Topic:
            class Consumer:
                class Message:
                    def __init__(self, value):
                        self.value = value

                def __init__(self, topic, *args, **kw):
                    self._topic = topic

                def consume(self, block=True):
                    if self._topic:
                        return self.Message(self._topic)

                def stop(self):
                    pass

            class Producer:
                def __init__(self, topic, *args, **kw):
                    self._topic = topic

                def produce(self, msg):
                    assert msg == self._topic

                def stop(self):
                    pass

            def __init__(self, topic):
                self._topic = topic

            def get_balanced_consumer(self, *args, **kw):
                return self.Consumer(self._topic, *args, **kw)

            def get_producer(self, *args, **kw):
                return self.Producer(self._topic, *args, **kw)

        def __getitem__(self, topic):
            assert isinstance(topic, bytes)
            return self.Topic(topic)

    def __init__(self, *args, **kw):
        self._topic_dict = self.TopicDict()

    @property
    def topics(self):
        return self._topic_dict


class NoneClient:
    class TopicDict:
        class Topic:
            class Consumer:
                def __init__(self, topic, *args, **kw):
                    self._topic = topic

                def consume(self, block=True):
                    return None

                def stop(self):
                    pass

            def __init__(self, topic):
                self._topic = topic

            def get_balanced_consumer(self, *args, **kw):
                return self.Consumer(self._topic, *args, **kw)

        def __getitem__(self, topic):
            assert isinstance(topic, bytes)
            return self.Topic(topic)

    def __init__(self, *args, **kw):
        self._topic_dict = self.TopicDict()

    @property
    def topics(self):
        return self._topic_dict


@pytest.fixture(scope="function")
def topic_consumer(request, monkeypatch):
    monkeypatch.setattr(mqcache, "KafkaClient", TopicClient)
    request.addfinalizer(lambda: monkeypatch.undo())


@pytest.fixture(scope="function")
def none_consumer(request, monkeypatch):
    monkeypatch.setattr(mqcache, "KafkaClient", NoneClient)
    request.addfinalizer(lambda: monkeypatch.undo())


def test_poll(topic_consumer):
    mq = MQCache.from_config(dict(mqcache_rpc_listen="0.0.0.0:7370",
                                  kafka_addr="",
                                  mqcache_queue_size=3,
                                  mqcache_sleep_time=0.1))
    mq.start()
    wait_server_start("127.0.0.1:7370")
    client = RpcClient("127.0.0.1:7370")
    assert client.poll() == (None, None)
    topics = set()
    for i in ("0", "1", "2"):
        topics.add(i)
    mq.subscribe(topics)
    time.sleep(0.2)
    a = [0] * len(topics)
    for i in range(2 * len(topics)):
        t, d = client.poll()
        assert t.encode("utf-8") == d
        a[int(t)] += 1
    for i in a:
        assert i == 2
    mq.stop()


def test_poll_none(none_consumer):
    mq = MQCache.from_config(dict(mqcache_rpc_listen="0.0.0.0:7371",
                                  kafka_addr="",
                                  mqcache_queue_size=3,
                                  mqcache_sleep_time=0.1))
    mq.start()
    wait_server_start("127.0.0.1:7371")
    client = RpcClient("127.0.0.1:7371")
    assert client.poll() == (None, None)
    topics = set()
    for i in ("0", "1", "2"):
        topics.add(i)
    mq.subscribe(topics)
    time.sleep(0.2)
    for i in range(2 * len(topics)):
        t, d = client.poll()
        assert t is None and d is None
    mq.stop()


def test_subscribe(topic_consumer, monkeypatch):
    def load_topic(topic):
        load_list.append(topic)

    def remove_topic(topic):
        remove_list.append(topic)

    mq = MQCache.from_config(dict(mqcache_rpc_listen="",
                                  kafka_addr=""))
    monkeypatch.setattr(mq, "_load_topic", load_topic)
    monkeypatch.setattr(mq, "_remove_topic", remove_topic)
    op = [[["0", "1"], ["0", "1"], []],
          [["2", "0", "1"], ["2"], []],
          [["1", "3", "2"], ["3"], ["0"]],
          [["2", "1"], [], ["3"]],
          [["4"], ["4"], ["1", "2"]],
          [[], [], ["4"]]]
    for i in op:
        load_list = []
        remove_list = []
        topics = set()
        for j in i[0]:
            topics.add(j)
        mq.subscribe(topics)
        assert sorted(load_list) == sorted(i[1])
        assert sorted(remove_list) == sorted(i[2])


def test_remove_topic(topic_consumer, monkeypatch):
    mq = MQCache.from_config(dict(mqcache_rpc_listen="",
                                  kafka_addr=""))
    topics = set()
    topics.add("0")
    topics.add("1")
    mq.subscribe(topics)
    mq._mq["0"].append(b"0")
    mq._remove_topic("1")
    mq._remove_topic("0")
