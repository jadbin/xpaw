# coding=utf-8


class NetworkError(Exception):
    """
    Error occurred when download.
    """


class IgnoreRequest(Exception):
    """
    Ignore this request.
    """


class ResponseNotMatch(Exception):
    """
    The response is not as desired.
    """


class UsageError(Exception):
    """
    CLI usage error.
    """

    def __init__(self, *args, **kwargs):
        self.print_help = kwargs.pop('print_help', True)
        super().__init__(*args, **kwargs)
