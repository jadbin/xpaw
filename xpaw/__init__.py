# coding=utf-8

# Add patch to avoid 'TIME_WAIT'
from . import _patch

from aiohttp import FormData

from .spider import Spider
from .http import HttpRequest, HttpResponse
from .selector import Selector
from .downloader import Downloader
from .item import Item, Field
from .handler import every

__all__ = ('FormData', 'HttpRequest', 'HttpResponse', 'Downloader', 'Spider', 'Selector',
           'Item', 'Field', 'every')

del _patch
