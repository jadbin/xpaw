# coding=utf-8


class NotEnabled(Exception):
    """
    Not enabled.
    """


class UsageError(Exception):
    """
    Command usage error.
    """

    def __init__(self, *args, print_help=False, **kwargs):
        self.print_help = print_help
        super().__init__(*args, **kwargs)


class ClientError(Exception):
    """
    Downloader client error.
    """


class IgnoreRequest(Exception):
    """
    Ignore this request.
    """


class HttpError(Exception):
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


class StopCrawler(Exception):
    """
    Stop crawler.
    """
