# coding=utf-8


from .version import __version__

# Add patch to avoid 'TIME_WAIT'
from . import _patch

del _patch

from .spider import Spider
from .http import HttpRequest, HttpResponse
from .selector import Selector
from .downloader import Downloader

from aiohttp import FormData

__all__ = ('__version__',
           'Spider', 'HttpRequest', 'HttpResponse', 'Selector', 'Downloader',
           'FormData')
