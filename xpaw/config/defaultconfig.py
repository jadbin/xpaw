# coding=utf-8

from os.path import abspath, join, dirname

log_file = None
log_encoding = "utf-8"
log_level = "INFO"
log_format = "%(asctime)s %(name)s [%(levelname)s]: %(message)s"
log_dateformat = "%Y-%m-%d %H:%M:%S"

templates_dir = abspath(join(dirname(__file__), "..", "templates"))

downloader_clients = 100
downloader_timeout = 20

queue_cls = "xpaw.queue.RequestDequeue"

dupefilter_cls = "xpaw.dupefilter.SetDupeFilter"

downloader_middlewares = []

spider_middlewares = []
