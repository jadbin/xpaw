.. _errors:

Errors
======

Built-in Errors
---------------

这里给出了内置的错误类型。


.. class:: xpaw.errors.NotEnabled

    在加载组件的时候抛出的异常，表示该组件未启用。

.. class:: xpaw.errors.ClientError

    在downloader发起请求过程中抛出的异常，例如服务器无法访问等。

.. class:: xpaw.errors.HttpError

    非2xx响应抛出的异常。

.. class:: xpaw.errors.IgnoreRequest

    在处理 :class:`~xpaw.http.HttpRequest` 时抛出的异常，表示忽略该request，例如到达了一定的重试次数等。

.. class:: xpaw.errors.IgnoreItem

    在处理 :class:`~xpaw.item.Item` 时抛出的异常，表示忽略该item。

.. class:: xpaw.errors.UsageError

    xpaw相关命令使用方法不正确时抛出的异常。

.. class:: xpaw.errors.CloseCrawler

    在spider的处理 :class:`~xpaw.http.HttpResponse` 的回调函数中可以抛出该异常，主动停止crawler。
