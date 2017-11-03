# coding=utf-8

import pytest

from xpaw.eventbus import EventBus

event1 = object()
event2 = object()


class MyClass:
    def __init__(self):
        self.count1 = 0
        self.count2 = 0
        self.value = 0

    def method(self):
        """
        method
        """

    @staticmethod
    def staticmethod():
        """
        static method
        """

    def method1(self):
        self.count1 += 1

    async def method2(self):
        self.count2 += 1

    def method_set_value(self, value):
        self.value = value

    def method_raise_error(self):
        raise RuntimeError('not an error actually')


def test_raise_value_error():
    def func():
        """
        function
        """

    eventbus = EventBus()
    with pytest.raises(ValueError):
        eventbus.subscribe(func, event1)
    with pytest.raises(ValueError):
        eventbus.subscribe(MyClass().staticmethod, event1)
    eventbus.subscribe(MyClass().method, event1)


async def test_subscribe():
    eventbus = EventBus()
    obj = MyClass()
    eventbus.subscribe(obj.method1, event1)
    eventbus.subscribe(obj.method2, event2)
    await eventbus.send(event1)
    assert obj.count1 == 1 and obj.count2 == 0
    await eventbus.send(event2)
    assert obj.count1 == 1 and obj.count2 == 1


async def test_subscribe_multi_times():
    eventbus = EventBus()
    obj = MyClass()
    eventbus.subscribe(obj.method1, event1)
    eventbus.subscribe(obj.method1, event1)
    await eventbus.send(event1)
    assert obj.count1 == 1


async def test_unsubscribe():
    eventbus = EventBus()
    obj = MyClass()
    eventbus.subscribe(obj.method1, event1)
    await eventbus.send(event1)
    assert obj.count1 == 1
    eventbus.unsubscribe(obj.method1, event1)
    await eventbus.send(event1)
    assert obj.count1 == 1


async def test_unsubscribe_multi_times():
    eventbus = EventBus()
    obj = MyClass()
    eventbus.subscribe(obj.method1, event1)
    eventbus.unsubscribe(obj.method1, event1)
    eventbus.unsubscribe(obj.method1, event1)


async def test_send_with_parameters():
    eventbus = EventBus()
    obj = MyClass()
    eventbus.subscribe(obj.method_set_value, event1)
    await eventbus.send(event1, value=-1)
    assert obj.value == -1


async def test_send_unknown_event():
    eventbus = EventBus()
    obj = MyClass()
    await eventbus.send(event1)
    eventbus.subscribe(obj.method1, event1)
    await eventbus.send(event2)
    assert obj.count1 == 0


async def test_unknown_unsubscribe():
    eventbus = EventBus()
    obj = MyClass()
    eventbus.subscribe(obj.method1, event1)
    eventbus.unsubscribe(obj.method1, event2)
    eventbus.unsubscribe(obj.method2, event1)
    eventbus.unsubscribe(obj.method, event2)
    await eventbus.send(event1)
    assert obj.count1 == 1


async def test_raise_error_in_callback():
    eventbus = EventBus()
    obj = MyClass()
    eventbus.subscribe(obj.method_raise_error, event1)
    await eventbus.send(event1)


async def test_del_weak_ref():
    eventbus = EventBus()
    obj1 = MyClass()
    obj2 = MyClass()
    eventbus.subscribe(obj1.method1, event1)
    eventbus.subscribe(obj2.method1, event1)
    await eventbus.send(event1)
    assert obj1.count1 == 1 and obj2.count1 == 1
    del obj2
    assert len(eventbus._refs[event1]) == 2
    await eventbus.send(event1)
    assert len(eventbus._refs[event1]) == 1
    assert obj1.count1 == 2
