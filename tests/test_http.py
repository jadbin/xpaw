# coding=utf-8

from xpaw.http import HttpRequest, HttpResponse


def test_copy_http_request():
    req = HttpRequest('http://httpbin.org/get', params={'show_env': 1}, meta={'depth': 0})
    copy_req = req.copy()
    assert copy_req.url == req.url
    assert 'show_env' in copy_req.params and copy_req.params['show_env'] == 1
    assert 'depth' in copy_req.meta and copy_req.meta['depth'] == 0
    req.meta['depth'] = 1
    assert req.meta['depth'] == 1 and copy_req.meta['depth'] == 0


def test_new_http_request():
    req = HttpRequest('http://httpbin.org/post', 'POST', body=b'body1')
    new_req = req.new(url='https://httpbin.org/post', body=b'body2')
    assert new_req.url == 'https://httpbin.org/post'
    assert new_req.body == b'body2'
    assert new_req.method == 'POST'


def test_copy_http_response():
    resp = HttpResponse('http://httpbin.org/get', 200, body=b'body')
    copy_resp = resp.copy()
    assert copy_resp.url == 'http://httpbin.org/get'
    assert copy_resp.status == 200
    assert copy_resp.body == b'body'


def test_new_http_response():
    resp = HttpResponse('http://httpbin.org/get', 200, body=b'body1')
    new_resp = resp.new(url='https://httpbin.org/get', body=b'body2')
    assert new_resp.url == 'https://httpbin.org/get'
    assert new_resp.status == 200
    assert new_resp.body == b'body2'
