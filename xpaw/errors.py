# coding=utf-8


class NotEnabled(Exception):
    """
    Not enabled.
    """


class NetworkError(Exception):
    """
    Network error.
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

    def __init__(self, *args, **kwargs):
        self.print_help = kwargs.pop('print_help', True)
        super().__init__(*args, **kwargs)
