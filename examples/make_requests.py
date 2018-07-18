# coding=utf-8

from xpaw import make_requests, HttpRequest

if __name__ == '__main__':
    requests = ['http://localhost', 'http://python.org', HttpRequest('http://python.org')]
    results = make_requests(requests)
    print(results)
