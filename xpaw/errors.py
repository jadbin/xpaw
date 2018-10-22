# coding=utf-8

import asyncio


class NotEnabled(Exception):
    """
    Not enabled.
    """


class UsageError(Exception):
    """
    CLI usage error.
    """

    def __init__(self, *args, print_help=False, **kwargs):
        self.print_help = print_help
        super().__init__(*args, **kwargs)


TimeoutError = asyncio.TimeoutError


class ClientError(Exception):
    """
    Downloader client error.
    """


class IgnoreRequest(Exception):
    """
    Ignore this request.
    """


class HttpError(IgnoreRequest):
    """
    HTTP status is not 2xx.
    """

    def __init__(self, *args, response=None, **kwargs):
        self.response = response
        super().__init__(*args, **kwargs)


class IgnoreItem(Exception):
    """
    Ignore this item.
    """


class StopCluster(Exception):
    """
    Stop cluster.
    """
