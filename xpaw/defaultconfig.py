# coding=utf-8

from os.path import abspath, join, dirname

from xpaw import __version__ as version

log_file = None
log_level = 'INFO'
log_format = '%(asctime)s %(name)s [%(levelname)s]: %(message)s'
log_dateformat = '%Y-%m-%d %H:%M:%S'

templates_dir = abspath(join(dirname(__file__), 'templates'))

stats_center_cls = 'xpaw.statscenter.StatsCenter'

queue_cls = 'xpaw.queue.PriorityQueue'

dupe_filter_cls = 'xpaw.dupefilter.SetDupeFilter'

downloader_clients = 100
downloader_timeout = 20
verify_ssl = True
cookie_jar_enabled = False

downloader_middlewares_base = {
    # cluster side
    'xpaw.downloadermws.SpeedLimitMiddleware': 100,
    'xpaw.downloadermws.DefaultHeadersMiddleware': 300,
    'xpaw.downloadermws.ImitatingProxyMiddleware': 350,
    'xpaw.downloadermws.UserAgentMiddleware': 400,
    'xpaw.downloadermws.RetryMiddleware': 500,
    'xpaw.downloadermws.ProxyMiddleware': 700
    # downloader side
}

spider_middlewares_base = {
    # cluster side
    'xpaw.spidermws.DepthMiddleware': 900
    # spider side
}

speed_limit_rate = None
speed_limit_burst = None

default_headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-CN,zh;q=0.8',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

user_agent = 'Mozilla/5.0 (compatible; xpaw/{})'.format(version)
random_user_agent = False

imitating_proxy_enabled = False

retry_enabled = True
max_retry_times = 3
retry_http_status = (500, 502, 503, 504, 408, 429)

proxy = None
proxy_agent = None

max_depth = None
