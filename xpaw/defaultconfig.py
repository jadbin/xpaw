# coding=utf-8

from os.path import abspath, join, dirname

log_file = None
log_encoding = "utf-8"
log_level = "INFO"
log_format = "%(asctime)s %(name)s [%(levelname)s]: %(message)s"
log_dateformat = "%Y-%m-%d %H:%M:%S"

templates_dir = abspath(join(dirname(__file__), "templates"))


queue_cls = "xpaw.queue.RequestQueue"

dupe_filter_cls = "xpaw.dupefilter.SetDupeFilter"

downloader_clients = 100
downloader_timeout = 20

downloader_middlewares = [
    "xpaw.downloadermws.RetryMiddleware"
]

spider_middlewares = []

extensions = []
