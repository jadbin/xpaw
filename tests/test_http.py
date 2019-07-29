# coding=utf-8

from xpaw.http import HttpRequest, HttpResponse, HttpHeaders
from xpaw.utils import get_params_in_url


def test_copy_http_request():
    req = HttpRequest('http://example.com/', params={'key': 'value'}, meta={'depth': 0})
    copy_req = req.copy()
    assert copy_req.url == req.url
    params = get_params_in_url(copy_req.url)
    assert 'key' in params and params['key'] == ['value']
    assert 'depth' in copy_req.meta and copy_req.meta['depth'] == 0
    req.meta['depth'] = 1
    assert req.meta['depth'] == 1 and copy_req.meta['depth'] == 0


def test_replace_http_request():
    req = HttpRequest('http://example.com/', 'POST', body=b'body1')
    new_req = req.replace(url='https://example.com/', body=b'body2')
    assert new_req.url == 'https://example.com/'
    assert new_req.body == b'body2'
    assert new_req.method == 'POST'


def test_http_request_to_dict():
    headers = HttpHeaders()
    headers.add('Set-Cookie', 'a=b')
    headers.add('Set-Cookie', 'c=d')
    req = HttpRequest('http://example.com/', 'POST', body=b'body', headers=headers)
    d = req.to_dict()
    assert d['url'] == 'http://example.com/'
    assert d['method'] == 'POST'
    assert d['body'] == b'body'
    assert d['headers'] == headers

    req2 = HttpRequest.from_dict(d)
    assert req.url == req2.url
    assert req.method == req2.method
    assert req.body == req2.body
    assert req.headers == req2.headers


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
