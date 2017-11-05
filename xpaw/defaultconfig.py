# coding=utf-8

from os.path import abspath, join, dirname

log_file = None
log_encoding = "utf-8"
log_level = "INFO"
log_format = "%(asctime)s %(name)s [%(levelname)s]: %(message)s"
log_dateformat = "%Y-%m-%d %H:%M:%S"

templates_dir = abspath(join(dirname(__file__), "templates"))

stats_center_cls = "xpaw.statscenter.StatsCenter"

queue_cls = "xpaw.queue.PriorityQueue"

dupe_filter_cls = "xpaw.dupefilter.SetDupeFilter"

downloader_clients = 100
downloader_timeout = 20
downloader_verify_ssl = True
downloader_cookie_jar_enabled = False

downloader_middlewares = [
    "xpaw.downloadermws.RetryMiddleware"
]

spider_middlewares = []

item_pipelines = []

extensions = []
