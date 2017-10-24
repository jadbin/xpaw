# coding=utf-8

import hashlib


def request_fingerprint(request):
    sha1 = hashlib.sha1()
    sha1.update(to_types(request.method))
    sha1.update(to_types(str(request.url)))
    sha1.update(request.body or b'')
    return sha1.hexdigest()


def to_types(data, encoding=None):
    if isinstance(data, bytes):
        return data
    if isinstance(data, str):
        return data.encode(encoding or "utf-8")
    raise TypeError("Need bytes or str, got {}".format(type(data).__name__))
