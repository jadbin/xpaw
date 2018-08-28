.. _make_requests:

Make Requests
=============

如果我们只是想下载URL对应的网页，但又不想写爬虫这么复杂的东西，那么我们可以直接借助 :func:`~xpaw.run.make_requests` 函数发起请求并获取结果。

.. code-block:: python

    from xpaw import make_requests, HttpRequest

    if __name__ == '__main__':
        requests = ['http://localhost', 'http://python.org', HttpRequest('http://python.org')]
        results = make_requests(requests)
        print(results)

请求可以是 ``str`` 或 :class:`~xpaw.http.HttpRequest` ，如果是 ``str`` 则认为提供的是 ``GET`` 请求的URL。

返回结果是一个 ``list`` ，和发起的请求一一对应，可能是 :class:`~xpaw.http.HttpResponse` , ``Exception`` 或 ``None`` 。
因此可以先通过 ``isinstance`` 判断是否是正常返回的结果 :class:`~xpaw.http.HttpResponse` 。
其次，如果是 ``Exception`` ，则表示请求出现了错误，例如常见的有 :class:`~xpaw.errors.IgnoreRequest` ，表示经过若干次重试之后依然没正常返回结果。
如果是 ``None`` ，一般是由请求的类型错误导致的。

使用 :func:`~xpaw.run.make_requests` 可以避免自己实现并发的代价，并提供了错误重试等诸多可选功能。

.. note::
    :func:`~xpaw.run.make_requests` 不可以在 :class:`~xpaw.spider.Spider` 中使用。
    其设计的初衷是我们可能面临这样的场景，只是想下载URL对应的网页，但又不想写爬虫这么复杂东西。
    此外，在 :class:`~xpaw.spider.Spider` 中处理请求的过程已经是并发的，因而也无需使用 :func:`~xpaw.run.make_requests` 。

.. function:: xpaw.run.make_requests(requests, **kwargs)

    :param requests: 请求列表
    :type requests: str or :class:`~xpaw.http.HttpRequest`
    :param kwargs: 相关配置参数，详见 :ref:`settings`
