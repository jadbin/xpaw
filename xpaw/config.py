# coding=utf-8

import copy
from collections import MutableMapping


class Config(MutableMapping):
    def __init__(self, __values=None, **kwargs):
        self.attrs = {}
        self.update(__values, **kwargs)

    def __getitem__(self, name):
        if name not in self:
            return None
        return self.attrs[name]

    def __contains__(self, name):
        return name in self.attrs

    def get(self, name, default=None):
        return self[name] if self[name] is not None else default

    def getbool(self, name, default=None):
        v = self.get(name, default)
        return getbool(v)

    def getint(self, name, default=None):
        v = self.get(name, default)
        return getint(v)

    def getfloat(self, name, default=None):
        v = self.get(name, default)
        return getfloat(v)

    def getlist(self, name, default=None):
        v = self.get(name, default)
        return getlist(v)

    def __setitem__(self, name, value):
        self.attrs[name] = value

    def set(self, name, value):
        self[name] = value

    def setdefault(self, k, default=None):
        if k not in self:
            self[k] = default

    def update(self, __values=None, **kwargs):
        if __values is not None:
            if isinstance(__values, Config):
                for name in __values:
                    self[name] = __values[name]
            else:
                for name, value in __values.items():
                    self[name] = value
        for k, v in kwargs.items():
            self[k] = v

    def delete(self, name):
        del self.attrs[name]

    def __delitem__(self, name):
        del self.attrs[name]

    def copy(self):
        return copy.deepcopy(self)

    def __iter__(self):
        return iter(self.attrs)

    def __len__(self):
        return len(self.attrs)


def getbool(v):
    try:
        return bool(int(v))
    except (ValueError, TypeError):
        if v in ("True", "true"):
            return True
        if v in ("False", "false"):
            return False
    return None


def getint(v):
    try:
        return int(v)
    except (ValueError, TypeError):
        pass
    return None


def getfloat(v):
    try:
        return float(v)
    except (ValueError, TypeError):
        pass
    return None


def getlist(v):
    if v is None:
        return None
    if isinstance(v, str):
        v = v.split(",")
    elif not hasattr(v, "__iter__"):
        v = [v]
    return list(v)


DEFAULT_CONFIG = {
    'daemon': False,
    'log_level': 'info',
    'log_format': '%(asctime)s %(name)s [%(levelname)s] %(message)s',
    'log_dateformat': '[%Y-%m-%d %H:%M:%S %z]',
    'downloader': 'xpaw.downloader.Downloader',
    'user_agent': ':desktop',
    'random_user_agent': False,
    'retry_enabled': True,
    'stats_collector': 'xpaw.stats.StatsCollector',
    'queue': 'xpaw.queue.PriorityQueue',
    'dupe_filter': 'xpaw.dupefilter.HashDupeFilter',
    'default_downloader_middlewares': {
        # crawler side
        'xpaw.downloader_middlewares.DefaultHeadersMiddleware': 300,
        'xpaw.downloader_middlewares.UserAgentMiddleware': 400,
        'xpaw.downloader_middlewares.RetryMiddleware': 500,
        'xpaw.downloader_middlewares.ProxyMiddleware': 700,
        'xpaw.downloader_middlewares.SpeedLimitMiddleware': 900,
        # downloader side
    },
    'default_spider_middlewares': {
        # crawler side
        'xpaw.spider_middlewares.DepthMiddleware': 900
        # spider side
    }
}
