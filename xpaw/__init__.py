# coding=utf-8


from .version import __version__

# Add patch to avoid 'TIME_WAIT'
from . import _patch

del _patch

from aiohttp import FormData

from .spider import Spider
from .http import HttpRequest, HttpResponse
from .selector import Selector
from .downloader import Downloader
from .item import Item, Field
from .handler import every

__all__ = ('__version__', 'FormData', 'HttpRequest', 'HttpResponse', 'Downloader', 'Spider', 'Selector',
           'Item', 'Field', 'every')
