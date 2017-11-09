# coding=utf-8

from os.path import abspath, join, dirname

from xpaw import __version__ as version

log_file = None
log_encoding = 'utf-8'
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
    'xpaw.downloadermws.DefaultHeadersMiddleware': 200,
    'xpaw.downloadermws.ImitatingProxyMiddleware': 300,
    'xpaw.downloadermws.RetryMiddleware': 600,
    'xpaw.downloadermws.ProxyMiddleware': 700
    # downloader side
}

spider_middlewares_base = {
    # cluster side
    'xpaw.spidermws.DepthMiddleware': 900
    # spider side
}

default_headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-CN,zh;q=0.8',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

user_agent = 'Mozilla/5.0 (compatible; xpaw/{})'.format(version)
