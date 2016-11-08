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


class RpcError(Exception):
    """
    RPC error.
    """


class UsageError(Exception):
    """
    CLI usage error.
    """
