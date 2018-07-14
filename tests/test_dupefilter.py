# coding=utf-8

from xpaw.http import HttpRequest
from xpaw.dupefilter import HashDupeFilter


def run_any_dupe_filter(f):
    r_get = HttpRequest("http://example.com")
    r_get_port_80 = HttpRequest("http://example.com:80")
    r_get_port_81 = HttpRequest("http://example.com:81")
    r_get_dont_filter = HttpRequest("http://example.com", dont_filter=True)
    r_get_dir = HttpRequest("http://example.com/")
    r_get_post = HttpRequest("http://example.com/post")
    r_post = HttpRequest("http://example.com/post", "POST")
    r_post_dir = HttpRequest("http://example.com/post/", "POST")
    r_post_data = HttpRequest("http://example.com/post", "POST", body=b'data')
    r_get_param = HttpRequest("http://example.com/get", params={'k1': 'v1'})
    r_get_query = HttpRequest("http://example.com/get?k1=v1")
    r_get_param_2 = HttpRequest("http://example.com/get", params={'k1': 'v1', 'k2': 'v2'})
    r_get_query_2 = HttpRequest("http://example.com/get?k2=v2&k1=v1")
    r_get_query_param = HttpRequest("http://example.com/get?k1=v1", params={'k2': 'v2'})
    assert f.is_duplicated(r_get) is False
    assert f.is_duplicated(r_get_port_80) is True
    assert f.is_duplicated(r_get_port_81) is False
    assert f.is_duplicated(r_get) is True
    assert f.is_duplicated(r_get_dont_filter) is False
    assert f.is_duplicated(r_get_dir) is True
    assert f.is_duplicated(r_get_post) is False
    assert f.is_duplicated(r_post) is False
    assert f.is_duplicated(r_post_dir) is False
    assert f.is_duplicated(r_post_data) is False
    assert f.is_duplicated(r_get_param) is False
    assert f.is_duplicated(r_get_query) is True
    assert f.is_duplicated(r_get_param_2) is False
    assert f.is_duplicated(r_get_query_2) is True
    assert f.is_duplicated(r_get_query_param) is True


class TestHashDupeFilter:
    def test_is_duplicated(self):
        run_any_dupe_filter(HashDupeFilter())

    def test_clear(self):
        f = HashDupeFilter()
        r_get = HttpRequest("http://example.com")
        assert f.is_duplicated(r_get) is False
        assert f.is_duplicated(r_get) is True
        f.clear()
        assert f.is_duplicated(r_get) is False

    def test_dump(self, tmpdir):
        f = HashDupeFilter(dump_dir=str(tmpdir))
        r_get = HttpRequest("http://example.com")
        assert f.is_duplicated(r_get) is False
        assert f.is_duplicated(r_get) is True
        f.close()
        f2 = HashDupeFilter(dump_dir=str(tmpdir))
        f2.open()
        assert f2.is_duplicated(r_get) is True
