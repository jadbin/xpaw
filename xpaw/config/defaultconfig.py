# coding=utf-8

from os.path import abspath, join, dirname

LOG_FILE = None
LOG_ENCODING = "utf-8"
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s %(name)s [%(levelname)s]: %(message)s"
LOG_DATEFORMAT = "%Y-%m-%d %H:%M:%S"

TEMPLATES_DIR = abspath(join(dirname(__file__), "..", "templates"))

DOWNLOADER_CLIENTS = 100
DOWNLOADER_TIMEOUT = 20

QUEUE_CLS = "xpaw.queue.RequestDequeue"
