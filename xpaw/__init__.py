# coding=utf-8

# Add patch to avoid 'TIME_WAIT'
from . import _patch

from aiohttp import FormData

from .spider import Spider, every
from .http import HttpRequest, HttpResponse
from .selector import Selector
from .downloader import Downloader
from .item import Item, Field

__all__ = ('FormData', 'HttpRequest', 'HttpResponse', 'Downloader', 'Spider', 'Selector',
           'Item', 'Field', 'every')

del _patch
