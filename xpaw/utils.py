# coding=utf-8

import os
import re
import cgi
import sys
import hashlib
import logging
from importlib import import_module
import string
from os.path import isfile, exists
import inspect

from yarl import URL

PY35 = sys.version_info >= (3, 5)
PY36 = sys.version_info >= (3, 6)


def load_object(path):
    if isinstance(path, str):
        dot = path.rindex(".")
        module, name = path[:dot], path[dot + 1:]
        mod = import_module(module)
        return getattr(mod, name)
    return path


def configure_logger(name, config):
    log_level = config.get('log_level').upper()
    log_format = config.get('log_format')
    log_dateformat = config.get('log_dateformat')
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    log_file = config.get('log_file')
    if log_file:
        handler = logging.FileHandler(log_file)
    else:
        handler = logging.StreamHandler()
    handler.setLevel(log_level)
    formatter = logging.Formatter(log_format, log_dateformat)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return handler


def remove_logger(name):
    logging.getLogger(name).handlers.clear()


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


def render_template_file(path, **kwargs):
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


def be_daemon():
    if os.fork():
        os._exit(0)
    os.setsid()
    if os.fork():
        os._exit(0)
    os.umask(0o22)
    os.closerange(0, 3)
    fd_null = os.open(os.devnull, os.O_RDWR)
    if fd_null != 0:
        os.dup2(fd_null, 0)
    os.dup2(fd_null, 1)
    os.dup2(fd_null, 2)


def load_config(fname):
    if fname is None or not isfile(fname):
        raise ValueError('{} is not a file'.format(fname))
    code = compile(open(fname, 'rb').read(), fname, 'exec')
    cfg = {
        "__builtins__": __builtins__,
        "__name__": "__config__",
        "__file__": fname,
        "__doc__": None,
        "__package__": None
    }
    exec(code, cfg, cfg)
    return cfg


def iter_settings(config):
    for key, value in config.items():
        if not key.startswith('_') and not inspect.ismodule(value) and not inspect.isfunction(value):
            yield key, value


def get_dump_dir(config):
    dump_dir = config.get('dump_dir')
    if dump_dir:
        if not exists(dump_dir):
            os.makedirs(dump_dir, 755)
        return dump_dir


def request_to_dict(request):
    callback = request.callback
    if inspect.ismethod(callback):
        callback = callback.__name__
    errback = request.errback
    if inspect.ismethod(errback):
        errback = errback.__name__
    meta = dict(request.meta)
    if 'cookie_jar' in meta:
        del meta['cookie_jar']
    d = {
        'url': request.url,
        'method': request.method,
        'body': request.body,
        'params': request.params,
        'headers': request.headers,
        'cookies': request.cookies,
        'meta': meta,
        'priority': request.priority,
        'dont_filter': request.dont_filter,
        'callback': callback,
        'errback': errback,
        '_class': request.__module__ + '.' + request.__class__.__name__
    }
    return d


def request_from_dict(d):
    req_cls = load_object(d.pop('_class'))
    return req_cls(**d)
