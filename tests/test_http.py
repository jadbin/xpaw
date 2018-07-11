# coding=utf-8

from xpaw.http import HttpRequest, HttpResponse


def test_copy_http_request():
    req = HttpRequest('http://example.com/', params={'key': 'value'}, meta={'depth': 0})
    copy_req = req.copy()
    assert copy_req.url == req.url
    assert 'key' in copy_req.params and copy_req.params['key'] == 'value'
    assert 'depth' in copy_req.meta and copy_req.meta['depth'] == 0
    req.meta['depth'] = 1
    assert req.meta['depth'] == 1 and copy_req.meta['depth'] == 0


def test_replace_http_request():
    req = HttpRequest('http://example.com/', 'POST', body=b'body1')
    new_req = req.replace(url='https://example.com/', body=b'body2')
    assert new_req.url == 'https://example.com/'
    assert new_req.body == b'body2'
    assert new_req.method == 'POST'


def test_copy_http_response():
    resp = HttpResponse('http://example.com/', 200, body=b'body')
    copy_resp = resp.copy()
    assert copy_resp.url == 'http://example.com/'
    assert copy_resp.status == 200
    assert copy_resp.body == b'body'


def test_replace_http_response():
    resp = HttpResponse('http://example.com/', 200, body=b'body1')
    new_resp = resp.replace(url='https://example.com/', body=b'body2')
    assert new_resp.url == 'https://example.com/'
    assert new_resp.status == 200
    assert new_resp.body == b'body2'
