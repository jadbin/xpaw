# coding=utf-8

import asyncio

TimeoutError = asyncio.TimeoutError


class NotEnabled(Exception):
    """
    Not enabled.
    """


class ClientError(Exception):
    """
    Downloader client error.
    """


class IgnoreRequest(Exception):
    """
    Ignore this request.
    """


class IgnoreItem(Exception):
    """
    Ignore this item.
    """


class UsageError(Exception):
    """
    CLI usage error.
    """


class StopCluster(Exception):
    """
    Stop cluster.
    """
