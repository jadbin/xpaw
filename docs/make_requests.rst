.. _make_requests:

Make Requests
=============

如果我们只是想下载URL对应的网页，但又不想写爬虫这么复杂的东西，那么我们可以直接借助 :func:`~xpaw.run.make_requests` 函数发起请求并获取结果。

.. code-block:: python

    from xpaw import make_requests, HttpRequest

    if __name__ == '__main__':
        requests = ['http://unknown', 'http://python.org', HttpRequest('http://python.org')]
        results = make_requests(requests)
        print(results)

请求可以是 ``str`` 或 :class:`~xpaw.http.HttpRequest` ，如果是 ``str`` 则认为提供的是 ``GET`` 请求的URL。

返回结果是一个 ``list`` ，和发起的请求一一对应，可能是 :class:`~xpaw.http.HttpResponse` 或 ``Exception`` 。
因此可以先通过 ``isinstance`` 判断是否是正常返回的结果 :class:`~xpaw.http.HttpResponse` 。
其次，如果是 ``Exception`` ，则表示请求出现了错误，例如常见的有 :class:`~xpaw.errors.ClientError` , :class:`~xpaw.errors.HttpError` (非2xx的HTTP状态码)。

使用 :func:`~xpaw.run.make_requests` 可以实现请求的并发执行，并提供了错误重试等诸多可选功能。

.. note::
    :func:`~xpaw.run.make_requests` 在 :class:`~xpaw.spider.Spider` 中使用会报错。
    在 :class:`~xpaw.spider.Spider` 中处理请求的过程已经是并发的，因而也无需使用 :func:`~xpaw.run.make_requests` 。

.. function:: xpaw.run.make_requests(requests, **kwargs)

    :param requests: 请求列表
    :type requests: str or :class:`~xpaw.http.HttpRequest`
    :param kwargs: 相关配置参数，详见 :ref:`settings`
