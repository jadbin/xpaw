# coding=utf-8

import json
import asyncio
import logging
from collections import deque

import aiohttp
from aiohttp import web
from pykafka import KafkaClient
from pykafka.exceptions import ConsumerStoppedException

log = logging.getLogger(__name__)

TOPIC_HEADER = "x-unikafka-topic"


class Unikafka:
    def __init__(self, server_listen, kafka_addr, zookeeper_addr, *, group=__name__,
                 queue_size=100, sleep_time=1,
                 loop=None):
        self._server_listen = server_listen
        self._kafka_addr = kafka_addr
        self._zookeeper_addr = zookeeper_addr
        self._group = group
        self._queue_size = queue_size
        self._sleep_time = sleep_time
        self._kafka_client = KafkaClient(hosts=self._kafka_addr,
                                         broker_version="0.9.2")
        self._mq, self._consumers = {}, {}
        self._topics = []
        self._index = 0
        self._loop = loop or asyncio.get_event_loop()
        self._is_running = False
        self._topic_lock = asyncio.Lock(loop=self._loop)

    @classmethod
    def from_config(cls, config):
        kw = {}
        if "unikafka_group" in config:
            kw["group"] = config["unikafka_group"]
        if "unikafka_queue_size" in config:
            kw["queue_size"] = config["unikafka_queue_size"]
        if "unikafka_sleep_time" in config:
            kw["sleep_time"] = config["unikafka_sleep_time"]
        if "unikafka_loop" in config:
            kw["loop"] = config["unikafka_loop"]
        return cls(config.get("unikafka_listen"),
                   config.get("kafka_addr"),
                   config.get("zookeeper_addr"),
                   **kw)

    def start(self):
        if not self._is_running:
            self._is_running = True
            asyncio.ensure_future(self._poll_forever(), loop=self._loop)
            app = web.Application(logger=log, loop=self._loop)
            app.router.add_get("/poll", self._poll)
            app.router.add_post("/subscribe", self._subscribe)
            host, port = self._server_listen.split(":")
            port = int(port)
            self._loop.run_until_complete(self._loop.create_server(app.make_handler(access_log=None), host, port))

    def stop(self):
        if self._is_running:
            self._is_running = False

    async def _poll(self, request):
        params = request.GET
        topic = params.get("topic")
        if not topic:
            if len(self._topics) > 0:
                i = self._index
                while True:
                    if len(self._mq[self._topics[i]]) > 0:
                        topic = self._topics[i]
                        i = 0 if i + 1 >= len(self._topics) else i + 1
                        break
                    i = 0 if i + 1 >= len(self._topics) else i + 1
                    if i == self._index:
                        break
                self._index = i
        if not topic:
            return web.Response(status=404)
        if topic not in self._mq:
            return web.Response(status=404, headers={TOPIC_HEADER: topic})
        data = await self.poll(topic)
        if data is None:
            return web.Response(status=204, headers={TOPIC_HEADER: topic})
        return web.Response(status=200, headers={TOPIC_HEADER: topic}, body=data)

    async def poll(self, topic):
        data = None
        mq = self._mq[topic]
        if len(mq) > 0:
            data = mq.popleft()
        return data

    async def _subscribe(self, request):
        body = await request.read()
        topic_list = json.loads(body.decode("utf-8"))
        await self.subscribe(topic_list)
        return web.Response(status=200)

    async def subscribe(self, topic_list):
        log.debug("Subscribe topics: {0}".format(topic_list))
        await self._topic_lock.acquire()
        new_set = set()
        for t in topic_list:
            new_set.add(t)
        old_set = set()
        for t in self._topics:
            old_set.add(t)
        for t in self._topics:
            if t not in new_set:
                self._remove_consumer(t)
        for t in topic_list:
            if t not in old_set:
                self._create_consumer(t)
        self._topics = topic_list
        self._index = 0
        self._topic_lock.release()

    async def _poll_forever(self):
        log.debug("Start to poll message")
        while self._is_running:
            no_work = True
            await self._topic_lock.acquire()
            try:
                for t in self._topics:
                    q = self._mq[t]
                    n, m = len(q), q.maxlen
                    if n < m:
                        msg = None
                        try:
                            msg = self._consumers[t].consume(block=True)
                        except ConsumerStoppedException:
                            log.warn("Consumer of topic '{0}' stopped".format(t))
                            self._remove_consumer(t)
                            self._create_consumer(t)
                            log.info("Reset consumer of topic '{0}'".format(t))
                            msg = self._consumers[t].consume(block=True)
                        finally:
                            if msg:
                                q.append(msg.value)
                                no_work = False
                    # take a very short break
                    await asyncio.sleep(0.001, loop=self._loop)
            except Exception:
                log.warning("Unexpected error occurred when poll message", exc_info=True)
            finally:
                self._topic_lock.release()
            if no_work:
                await asyncio.sleep(self._sleep_time, loop=self._loop)

    def _create_consumer(self, topic):
        q = deque(maxlen=self._queue_size)
        self._mq[topic] = q
        self._kafka_client.update_cluster()
        self._consumers[topic] = self._kafka_client.topics[topic.encode("utf-8")].get_balanced_consumer(
            consumer_group=self._group.encode("utf-8"),
            auto_commit_enable=True,
            zookeeper_connect=self._zookeeper_addr,
            consumer_timeout_ms=10)

    def _remove_consumer(self, topic):
        q = self._mq[topic]
        if len(q) > 0:
            producer = None
            try:
                self._kafka_client.update_cluster()
                producer = self._kafka_client.topics[topic.encode("utf-8")].get_producer(linger_ms=100)
                while len(q) > 0:
                    b = q.popleft()
                    producer.produce(b)
            except Exception:
                log.warning("Unexpected error occurred when save the cache of topic '{0}'".format(topic), exc_info=True)
            finally:
                if producer:
                    producer.stop()
        del self._mq[topic]
        self._consumers[topic].stop()
        del self._consumers[topic]


class UnikafkaClient:
    def __init__(self, unikafka_addr, *, timeout=10, loop=None):
        if not unikafka_addr.startswith("http://"):
            unikafka_addr = "http://{0}".format(unikafka_addr)
        self._unikafka_addr = unikafka_addr
        self._timeout = timeout
        self._loop = loop or asyncio.get_event_loop()
        self._session = aiohttp.ClientSession(loop=self._loop)

    @classmethod
    def from_config(cls, config):
        kw = {}
        if "unikafka_client_timeout" in config:
            kw["timeout"] = config["unikafka_client_timeout"]
        kw["loop"] = config.get("unikafka_client_loop")
        return cls(config.get("unikafka_addr"), **kw)

    async def subscribe(self, topic_list):
        async with self._session.post("{0}/{1}".format(self._unikafka_addr, "subscribe"),
                                      data=json.dumps(topic_list).encode("utf-8"),
                                      timeout=self._timeout) as resp:
            if resp.status == 200:
                return True
            return False

    async def poll(self, topic=None):
        params = {}
        if topic:
            params["topic"] = topic
        async with aiohttp.ClientSession(loop=self._loop) as session:
            async with session.get("{0}/{1}".format(self._unikafka_addr, "poll"),
                                   params=params,
                                   timeout=self._timeout) as resp:
                if resp.status == 200:
                    body = await resp.read()
                    return resp.headers.get(TOPIC_HEADER), body
                if resp.status == 204:
                    return resp.headers.get(TOPIC_HEADER), None
                return None, None

    def close(self):
        self._session.close()
