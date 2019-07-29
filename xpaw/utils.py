# coding=utf-8

import os
import re
import sys
import hashlib
import logging
from importlib import import_module
import string
from os.path import isfile
from urllib.parse import urlsplit, parse_qsl, urlencode, parse_qs
import cgi

from tornado.httputil import url_concat

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


def configure_tornado_logger(handlers):
    log = logging.getLogger('tornado')
    if log.handlers:
        return
    log.handlers = handlers
    log.setLevel('WARNING')


def request_fingerprint(request):
    sha1 = hashlib.sha1()
    sha1.update(to_bytes(request.method))
    res = urlsplit(request.url)
    queries = parse_qsl(res.query)
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


async def iterable_to_list(gen):
    res = []
    if gen is not None:
        if hasattr(gen, '__aiter__'):
            async for r in gen:
                res.append(r)
        else:
            for r in gen:
                res.append(r)
    return res


def cmp(a, b):
    return (a > b) - (a < b)


def daemonize():
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


def get_encoding_from_content_type(content_type):
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


def make_url(url, params=None):
    args = []
    if isinstance(params, dict):
        for k, v in params.items():
            if isinstance(v, (tuple, list)):
                for i in v:
                    args.append((k, i))
            else:
                args.append((k, v))
    elif isinstance(params, (tuple, list)):
        for k, v in params:
            args.append((k, v))
    return url_concat(url, args)


def get_params_in_url(url):
    return parse_qs(urlsplit(url).query)


def with_not_none_params(**kwargs):
    params = {}
    for k, v in kwargs.items():
        if v is not None:
            params[k] = v
    return params
