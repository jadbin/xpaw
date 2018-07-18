# coding=utf-8

# Add patch to avoid 'TIME_WAIT'
from . import _patch

from aiohttp import FormData

from .http import HttpRequest, HttpResponse
from .downloader import Downloader
from .spider import Spider, every
from .selector import Selector
from .item import Item, Field
from .run import run_spider, run_crawler, make_requests

__all__ = ['FormData',
           'HttpRequest', 'HttpResponse',
           'Downloader',
           'Spider', 'every',
           'Selector',
           'Item', 'Field',
           'run_spider', 'run_crawler', 'make_requests']

del _patch
