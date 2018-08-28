# coding=utf-8

import copy
from collections import MutableMapping
import inspect


class BaseConfig(MutableMapping):
    def __init__(self, values=None):
        self.attributes = {}
        self.update(values)

    def __getitem__(self, opt_name):
        if opt_name not in self:
            return None
        return self.attributes[opt_name]

    def __contains__(self, name):
        return name in self.attributes

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
        self.set(name, value)

    def set(self, name, value):
        self.attributes[name] = value

    def update(self, values):
        if values is not None:
            if isinstance(values, BaseConfig):
                for name in values:
                    self.set(name, values[name])
            else:
                for name, value in values.items():
                    self.set(name, value)

    def delete(self, name):
        del self.attributes[name]

    def __delitem__(self, name):
        del self.attributes[name]

    def copy(self):
        return copy.deepcopy(self)

    def __iter__(self):
        return iter(self.attributes)

    def __len__(self):
        return len(self.attributes)


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


class Config(BaseConfig):
    def __init__(self, values=None):
        super().__init__()
        for v in KNOWN_SETTINGS.values():
            self.set(v.name, v.value)
        self.update(values)


class Setting:
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
    default = 'INFO'
    short_desc = 'log level: DEBUG, INFO, WARNING, ERROR'


class LogFormat(Setting):
    name = 'log_format'
    default = '%(asctime)s %(name)s [%(levelname)s] %(message)s'


class LogDateformat(Setting):
    name = 'log_dateformat'
    default = '%Y-%m-%d %H:%M:%S'


class DownloaderClients(Setting):
    name = 'downloader_clients'
    cli = ['--downloader-clients']
    metavar = 'INT'
    type = int
    default = 100
    short_desc = 'the maximum number of simultaneous clients'


class DownloaderTimeout(Setting):
    name = 'downloader_timeout'
    cli = ['--downloader-timeout']
    metavar = 'FLOAT'
    type = float
    default = 20
    short_desc = 'timeout of downloader in seconds'


class VerifySsl(Setting):
    name = 'verify_ssl'
    default = False


class AllowRedirects(Setting):
    name = 'allow_redirects'
    default = True


class CookieJarEnabled(Setting):
    name = 'cookie_jar_enabled'
    cli = ['--cookie-jar-enabled']
    action = 'store_true'
    default = False
    short_desc = 'enable cookie jar'


class DefaultHeaders(Setting):
    name = 'default_headers'
    default = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.8',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }


class UserAgent(Setting):
    name = 'user_agent'
    default = ':desktop'


class RandomUserAgent(Setting):
    name = 'random_user_agent'
    default = False


class ImitatingProxyEnabled(Setting):
    name = 'imitating_proxy_enabled'
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
    default = (500, 502, 503, 504, 408, 429)


class SpeedLimitEnabled(Setting):
    name = 'speed_limit_enabled'
    default = False


class SpeedLimitRate(Setting):
    name = 'speed_limit_rate'
    default = 1


class SpeedLimitBurst(Setting):
    name = 'speed_limit_burst'
    default = 1


class MaxDepth(Setting):
    name = 'max_depth'
    cli = ['--max-depth']
    metavar = 'INT'
    type = int
    short_desc = 'maximum depth of spider'


class StatsCenter(Setting):
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


class DownloaderMiddlewaresBase(Setting):
    name = 'downloader_middlewares_base'
    default = {
        # cluster side
        'xpaw.downloadermws.DefaultHeadersMiddleware': 300,
        'xpaw.downloadermws.ImitatingProxyMiddleware': 350,
        'xpaw.downloadermws.UserAgentMiddleware': 400,
        'xpaw.downloadermws.RetryMiddleware': 500,
        'xpaw.downloadermws.CookiesMiddleware': 600,
        'xpaw.downloadermws.ProxyMiddleware': 700,
        'xpaw.downloadermws.SpeedLimitMiddleware': 900,
        # downloader side
    }


class SpiderMiddlewares(Setting):
    name = 'spider_middlewares'


class SpiderMiddlewaresBase(Setting):
    name = 'spider_middlewares_base'
    default = {
        # cluster side
        'xpaw.spidermws.DepthMiddleware': 900
        # spider side
    }


class ItemPipelines(Setting):
    name = 'item_pipelines'


class Extensions(Setting):
    name = 'extensions'


KNOWN_SETTINGS = {}

for _v in list(vars().values()):
    if inspect.isclass(_v) and issubclass(_v, Setting) and _v.name is not None:
        KNOWN_SETTINGS[_v.name] = _v()
