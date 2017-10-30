# coding=utf-8

from xpaw.http import HttpRequest
from xpaw.dupefilter import SetDupeFilter


async def run_any_dupe_filter(f):
    r_get = HttpRequest("http://httpbin.org")
    r_get_dir = HttpRequest("http://httpbin.org/")
    r_get_post = HttpRequest("http://httpbin.org/post")
    r_post = HttpRequest("http://httpbin.org/post", "POST")
    r_post_dir = HttpRequest("http://httpbin.org/post/", "POST")
    r_post_data = HttpRequest("http://httpbin.org/post", "POST", body=b'data')
    r_get_param = HttpRequest("http://httpbin.org/get", params={'k1': 'v1'})
    r_get_query = HttpRequest("http://httpbin.org/get?k1=v1")
    r_get_param_2 = HttpRequest("http://httpbin.org/get", params={'k1': 'v1', 'k2': 'v2'})
    r_get_query_2 = HttpRequest("http://httpbin.org/get?k2=v2&k1=v1")
    r_get_query_param = HttpRequest("http://httpbin.org/get?k1=v1", params={'k2': 'v2'})
    assert await f.is_duplicated(r_get) is False
    assert await f.is_duplicated(r_get_dir) is True
    assert await f.is_duplicated(r_get_post) is False
    assert await f.is_duplicated(r_post) is False
    assert await f.is_duplicated(r_post_dir) is False
    assert await f.is_duplicated(r_post_data) is False
    assert await f.is_duplicated(r_get_param) is False
    assert await f.is_duplicated(r_get_query) is True
    assert await f.is_duplicated(r_get_param_2) is False
    assert await f.is_duplicated(r_get_query_2) is True
    assert await f.is_duplicated(r_get_query_param) is True


async def test_set_dupe_filter():
    await run_any_dupe_filter(SetDupeFilter())
