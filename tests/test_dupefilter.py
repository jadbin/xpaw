# coding=utf-8

from xpaw.http import HttpRequest
from xpaw.dupefilter import SetDupeFilter


def test_set_dupe_filter():
    f = SetDupeFilter()
    f.open()
    r1 = HttpRequest("http://httpbin.org")
    r2 = HttpRequest("http://httpbin.org/")
    r3 = HttpRequest("http://httpbin.org", "POST")
    r4 = HttpRequest("http://httpbin.org", "POST", body=b'data')
    r5 = HttpRequest("http://httpbin.org/")
    assert f.is_duplicated(r1) is False
    assert f.is_duplicated(r2) is False
    assert f.is_duplicated(r3) is False
    assert f.is_duplicated(r4) is False
    assert f.is_duplicated(r5) is True
    f.close()
