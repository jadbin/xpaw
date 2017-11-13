# coding=utf-8

import os
import re
import cgi
import sys
import hashlib
import logging
from importlib import import_module
import string
from urllib.parse import urlsplit

from yarl import URL
from multidict import MultiDict
from aiohttp.helpers import BasicAuth

PY35 = sys.version_info >= (3, 5)
PY36 = sys.version_info >= (3, 6)


def load_object(path):
    if isinstance(path, str):
        dot = path.rindex(".")
        module, name = path[:dot], path[dot + 1:]
        mod = import_module(module)
        return getattr(mod, name)
    return path


def configure_logging(name, config):
    log_level = config.get('log_level')
    log_format = config.get('log_format')
    log_dateformat = config.get('log_dateformat')
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    filename = config.get('log_file')
    if filename:
        handler = logging.FileHandler(filename)
    else:
        handler = logging.StreamHandler()
    handler.setLevel(log_level)
    formatter = logging.Formatter(log_format, log_dateformat)
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def get_encoding_from_header(content_type):
    if content_type:
        content_type, params = cgi.parse_header(content_type)
        if "charset" in params:
            return params["charset"]


_charset_flag = re.compile(r"""<meta.*?charset=["']*(.+?)["'>]""", flags=re.I)
_pragma_flag = re.compile(r"""<meta.*?content=["']*;?charset=(.+?)["'>]""", flags=re.I)
_xml_flag = re.compile(r"""^<\?xml.*?encoding=["']*(.+?)["'>]""")


def get_encoding_from_content(content):
    if isinstance(content, bytes):
        content = content.decode("ascii", errors="ignore")
    elif not isinstance(content, str):
        raise ValueError("content should be bytes or str")
    s = _charset_flag.search(content)
    if s:
        return s.group(1).strip()
    s = _pragma_flag.search(content)
    if s:
        return s.group(1).strip()
    s = _xml_flag.search(content)
    if s:
        return s.group(1).strip()


def request_fingerprint(request):
    sha1 = hashlib.sha1()
    sha1.update(to_bytes(request.method))
    if isinstance(request.url, str):
        url = URL(request.url)
    else:
        url = request.url
    queries = []
    for k, v in url.query.items():
        queries.append('{}={}'.format(k, v))
    if request.params:
        for k, v in request.params.items():
            queries.append('{}={}'.format(k, v))
    queries.sort()
    sha1.update(to_bytes('{}://{}{}:{}?{}'.format(url.scheme, url.host, url.path, url.port, '&'.join(queries))))
    sha1.update(request.body or b'')
    return sha1.hexdigest()


def to_bytes(data, encoding=None):
    if isinstance(data, bytes):
        return data
    if isinstance(data, str):
        return data.encode(encoding or "utf-8")
    raise TypeError("Need bytes or str, got {}".format(type(data).__name__))


def render_templatefile(path, **kwargs):
    if path.endswith(".tmpl"):
        with open(path, "rb") as f:
            raw = f.read().decode("utf-8")

        content = string.Template(raw).substitute(**kwargs)

        render_path = path[:-len(".tmpl")]
        with open(render_path, "wb") as f:
            f.write(content.encode("utf-8"))
        os.remove(path)


_camelcase_invalid_chars = re.compile('[^a-zA-Z\d]')


def string_camelcase(s):
    return _camelcase_invalid_chars.sub('', s.title())


class AsyncGenWrapper:
    def __init__(self, gen):
        if not gen:
            gen = ()
        self.iter = gen.__iter__()

    async def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.iter)
        except StopIteration:
            raise StopAsyncIteration


async def iterable_to_list(gen):
    res = []
    if not hasattr(gen, '__aiter__'):
        gen = AsyncGenWrapper(gen)
    async for r in gen:
        res.append(r)
    return res


def cmp(a, b):
    return (a > b) - (a < b)


def parse_params(params):
    if isinstance(params, dict):
        res = MultiDict()
        for k, v in params.items():
            if isinstance(v, (tuple, list)):
                for i in v:
                    res.add(k, i)
            else:
                res.add(k, v)
        params = res
    return params


def parse_auth(auth):
    if isinstance(auth, (tuple, list)):
        auth = BasicAuth(*auth)
    elif isinstance(auth, str):
        auth = BasicAuth(*auth.split(':', 1))
    return auth


def parse_url(url):
    if isinstance(url, str):
        res = urlsplit(url)
        if res.scheme == '':
            url = 'http://{}'.format(url)
        url = URL(url)
    return url
