# coding=utf-8

# Add patch to avoid 'TIME_WAIT'
from . import _patch

from .http import FormData, URL, MultiDict, CIMultiDict, HttpRequest, HttpResponse
from .downloader import Downloader
from .spider import Spider, every
from .selector import Selector
from .item import Item, Field
from .run import run_spider, run_crawler, make_requests

__all__ = ['FormData', 'URL', 'MultiDict', 'CIMultiDict', 'HttpRequest', 'HttpResponse',
           'Downloader',
           'Spider', 'every',
           'Selector',
           'Item', 'Field',
           'run_spider', 'run_crawler', 'make_requests']

del _patch
