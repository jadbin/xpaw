# coding=utf-8

from .version import __version__

# Add patch to avoid 'TIME_WAIT'
from . import _patch

del _patch
