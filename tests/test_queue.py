# coding=utf-8

from xpaw.queue import RequestDequeue


def test_request_queue():
    q = RequestDequeue()
    q.open()
    assert q.pop() is None
    obj_list = [1, 2, 3]
    for o in obj_list:
        q.push(o)
    for i in range(len(obj_list)):
        assert q.pop() == obj_list[i]
    assert q.pop() is None
    q.close()
