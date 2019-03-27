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


KNOWN_SETTINGS = []


def make_settings():
    settings = []
    for s in KNOWN_SETTINGS:
        setting = s()
        if setting.cli is not None:
            settings.append(setting)
    return settings


class SettingMeta(type):
    def __new__(mcs, name, bases, attrs):
        parents = [b for b in bases if isinstance(b, SettingMeta)]
        if not parents:
            return type.__new__(mcs, name, bases, attrs)
        new_class = type.__new__(mcs, name, bases, attrs)
        KNOWN_SETTINGS.append(new_class)
        return new_class


class Setting(metaclass=SettingMeta):
    name = None
    cli = None
    metavar = None
    default = None
    action = None
    type = None
    nargs = None
    short_desc = None

    def __init__(self):
        self.value = self.default

    def add_argument(self, parser):
        if self.cli is None:
            return
        args = tuple(self.cli)
        kwargs = {'dest': self.name, 'help': '{} (default: {})'.format(self.short_desc, self.default)}
        if self.metavar is not None:
            kwargs['metavar'] = self.metavar
        if self.action is not None:
            kwargs['action'] = self.action
        if self.type is not None:
            kwargs['type'] = self.type
        if self.nargs is not None:
            kwargs['nargs'] = self.nargs
        parser.add_argument(*args, **kwargs)


class Daemon(Setting):
    name = 'daemon'
    cli = ['-d', '--daemon']
    action = 'store_true'
    default = False
    short_desc = 'run in daemon mode'


class PidFile(Setting):
    name = 'pid_file'
    cli = ['--pid-file']
    metavar = 'FILE'
    short_desc = 'PID file'


class DumpDir(Setting):
    name = 'dump_dir'
    cli = ['--dump-dir']
    metavar = 'DIR'
    short_desc = 'the directory to dump the state of a single job'


class LogFile(Setting):
    name = 'log_file'
    cli = ['--log-file']
    metavar = 'FILE'
    short_desc = 'log file'


class LogLevel(Setting):
    name = 'log_level'
    cli = ['-l', '--log-level']
    metavar = 'LEVEL'
    default = 'info'
    short_desc = 'log level'


class LogFormat(Setting):
    name = 'log_format'
    default = '%(asctime)s %(name)s [%(levelname)s] %(message)s'


class LogDateformat(Setting):
    name = 'log_dateformat'
    default = '[%Y-%m-%d %H:%M:%S %z]'


class Downloader(Setting):
    name = 'downloader'
    default = 'xpaw.downloader.Downloader'


class DownloaderClients(Setting):
    name = 'downloader_clients'
    cli = ['--downloader-clients']
    metavar = 'INT'
    type = int
    default = 100
    short_desc = 'the maximum number of simultaneous clients'


class DefaultHeaders(Setting):
    name = 'default_headers'


class UserAgent(Setting):
    name = 'user_agent'
    default = ':desktop'


class RandomUserAgent(Setting):
    name = 'random_user_agent'
    default = False


class Proxy(Setting):
    name = 'proxy'


class RetryEnabled(Setting):
    name = 'retry_enabled'
    default = True


class MaxRetryTimes(Setting):
    name = 'max_retry_times'
    default = 3


class RetryHttpStatus(Setting):
    name = 'retry_http_status'
    default = None


class SpeedLimitRate(Setting):
    name = 'speed_limit_rate'
    default = None


class SpeedLimitBurst(Setting):
    name = 'speed_limit_burst'
    default = None


class MaxDepth(Setting):
    name = 'max_depth'
    cli = ['--max-depth']
    metavar = 'INT'
    type = int
    short_desc = 'maximum depth of spider'


class StatsCollector(Setting):
    name = 'stats_collector'
    default = 'xpaw.stats.StatsCollector'


class Queue(Setting):
    name = 'queue'
    default = 'xpaw.queue.PriorityQueue'


class DupeFilter(Setting):
    name = 'dupe_filter'
    default = 'xpaw.dupefilter.HashDupeFilter'


class Spider(Setting):
    name = 'spider'


class DownloaderMiddlewares(Setting):
    name = 'downloader_middlewares'


class DefaultDownloaderMiddlewares(Setting):
    name = 'default_downloader_middlewares'
    default = {
        # crawler side
        'xpaw.downloader_middlewares.DefaultHeadersMiddleware': 300,
        'xpaw.downloader_middlewares.UserAgentMiddleware': 400,
        'xpaw.downloader_middlewares.RetryMiddleware': 500,
        'xpaw.downloader_middlewares.ProxyMiddleware': 700,
        'xpaw.downloader_middlewares.SpeedLimitMiddleware': 900,
        # downloader side
    }


class SpiderMiddlewares(Setting):
    name = 'spider_middlewares'


class DefaultSpiderMiddlewares(Setting):
    name = 'default_spider_middlewares'
    default = {
        # crawler side
        'xpaw.spider_middlewares.DepthMiddleware': 900
        # spider side
    }


class ItemPipelines(Setting):
    name = 'item_pipelines'


class Extensions(Setting):
    name = 'extensions'


DEFAULT_CONFIG = {s.name: s.default for s in KNOWN_SETTINGS}
