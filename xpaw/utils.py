# coding=utf-8

import os
import re
import sys
import hashlib
import logging
from importlib import import_module
import string
from os.path import isfile, exists
import inspect
from urllib.parse import urlsplit, parse_qsl, urlencode

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
    logger.handlers.clear()
    logger.addHandler(handler)
    return logger


def redirect_logger(name, logger, override=True):
    log = logging.getLogger(name)
    if log.handlers and not override:
        return
    log.handlers = logger.handlers
    log.setLevel(logger.level)


def request_fingerprint(request):
    sha1 = hashlib.sha1()
    sha1.update(to_bytes(request.method))
    res = urlsplit(request.url)

    queries = parse_qsl(res.query)
    if request.params is not None:
        if isinstance(request.params, dict):
            queries.extend(request.params.items())
        elif isinstance(request.params, (tuple, list)):
            queries.extend(request.params)
    queries.sort()
    final_query = urlencode(queries)
    sha1.update(to_bytes('{}://{}{}:{}?{}'.format(res.scheme,
                                                  '' if res.hostname is None else res.hostname,
                                                  res.path,
                                                  80 if res.port is None else res.port,
                                                  final_query)))
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


_camelcase_invalid_chars = re.compile(r'[^a-zA-Z\d]')


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
        if not key.startswith('_'):
            yield key, value


def get_dump_dir(config):
    dump_dir = config.get('dump_dir')
    if dump_dir:
        if not exists(dump_dir):
            os.makedirs(dump_dir, 0o755)
        return dump_dir


def request_to_dict(request):
    callback = request.callback
    if inspect.ismethod(callback):
        callback = callback.__name__
    errback = request.errback
    if inspect.ismethod(errback):
        errback = errback.__name__
    meta = dict(request.meta)
    d = {
        'url': request.url,
        'method': request.method,
        'body': request.body,
        'params': request.params,
        'headers': request.headers,
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
