# coding=utf-8

import time
import asyncio
import threading

import pytest

from xpaw import unikafka
from xpaw.unikafka import Unikafka, UnikafkaClient

from .helpers import wait_server_start


class Consumer:
    class Message:
        def __init__(self, value):
            self.value = value

    def __init__(self, topic, *args, **kw):
        self._topic = topic

    def consume(self):
        if self._topic == "None":
            return None
        if self._topic:
            return self.Message(self._topic.encode("utf-8"))

    def __iter__(self):
        return self

    def __next__(self):
        return self.consume()


class Producer:
    def __init__(self, *args, **kw):
        pass

    def produce(self, topic, msg):
        assert topic == msg


@pytest.fixture(scope="function")
def kafka_env(request, monkeypatch):
    monkeypatch.setattr(unikafka, "KafkaConsumer", Consumer)
    monkeypatch.setattr(unikafka, "KafkaProducer", Producer)
    request.addfinalizer(lambda: monkeypatch.undo())

    def handle_error(loop, context):
        pass

    def run():
        try:
            loop.run_forever()
        except Exception:
            pass
        finally:
            loop.close()

    def stop_loop():
        loop.call_soon_threadsafe(loop.stop)

    loop = asyncio.new_event_loop()
    loop.set_exception_handler(handle_error)
    server = Unikafka.from_config({"unikafka_listen": "0.0.0.0:7370",
                                   "unikafka_queue_size": 3,
                                   "unikafka_sleep_time": 0.1,
                                   "unikafka_loop": loop})
    server.start()
    t = threading.Thread(target=run)
    t.start()
    wait_server_start("127.0.0.1:7370")
    request.addfinalizer(stop_loop)
    return server


def test_subscribe_and_poll(kafka_env):
    async def _test():
        assert await client.poll() == (None, None)
        await client.subscribe(["None"])
        time.sleep(0.2)
        assert await client.poll() == (None, None)
        assert await client.poll("None") == ("None", None)
        topics = ["0", "1", "2"]
        await client.subscribe(topics)
        time.sleep(0.2)
        assert await client.poll("1") == ("1", b"1")
        a = [0] * len(topics)
        for i in range(2 * len(topics)):
            t, d = await client.poll()
            assert t.encode("utf-8") == d
            a[int(t)] += 1
        for i in a:
            assert i == 2
        await client.subscribe(["None"])
        time.sleep(0.2)
        assert await client.poll() == (None, None)
        assert await client.poll("None") == ("None", None)
        client.close()

    loop = asyncio.new_event_loop()
    client = UnikafkaClient.from_config({"unikafka_addr": "http://127.0.0.1:7370",
                                         "unikafka_client_loop": loop})
    loop.run_until_complete(_test())
    client.close()
