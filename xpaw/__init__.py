# coding=utf-8

__all__ = ["__version__", "Spider", "HttpRequest", "HttpResponse", "Selector"]

from .version import __version__

# Add patch to avoid 'TIME_WAIT'
from . import _patch

del _patch

from xpaw.spider import Spider
from xpaw.http import HttpRequest, HttpResponse
from xpaw.selector import Selector
