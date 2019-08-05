.. _req_resp:

Request & Response
==================

我们通过 :class:`~xpaw.http.HttpRequest` 和 :class:`~xpaw.http.HttpResponse` 封装爬取的请求和对应的结果。

通常情况下， :class:`~xpaw.http.HttpRequest` 一部分来自于spider中 :meth:`~xpaw.spider.Spider.start_requests` 方法生成的初始请求，另一部分来自于 :meth:`~xpaw.spider.Spider.parse` 方法解析页面得到的新的请求。
针对每个 :class:`~xpaw.http.HttpRequest` ，如果请求成功xpaw会生成对应的 :class:`~xpaw.http.HttpResponse` ，一般无需我们自己去构造 :class:`~xpaw.http.HttpResponse` 。

Request API
-----------

.. class:: xpaw.http.HttpRequest(url, method="GET", body=None, params=None, headers=None, proxy=None, timeout=20, verify_ssl=False, allow_redirects=True, auth=None, proxy_auth=None, priority=None, dont_filter=False, callback=None, errback=None, meta=None, render=None)

    用户通过此类封装HTTP请求。

    :param url: URL地址
    :type url: str or :class:`~xpaw.http.URL`
    :param str method: HTTP method，``GET`` 、 ``POST`` 等
    :param body: 请求发送的数据。如果类型为 ``dict`` ，会默认为发送json格式的数据。
    :type body: bytes or str or dict
    :param params: 请求参数
    :type params: dict
    :param headers: HTTP headers
    :type headers: dict or :class:`~xpaw.http.HttpHeaders`
    :param str proxy: 代理地址
    :param float timeout: 请求超时时间
    :param bool verify_ssl: 是否校验SSL
    :param bool allow_redirects: 是否自动重定向
    :param tuple auth: 认证信息，用户名和密码
    :param tuple proxy_auth: 代理认证信息，用户名和密码
    :param float priority: 请求的优先级
    :param bool dont_filter: 是否经过去重过滤器
    :param callback: 请求成功时的回调函数，必须是spider的成员函数，也可以传递递函数名称
    :type callback: str or method
    :param errback: 请求失败时的回调函数，必须是spider的成员函数，也可以传递函数名称
    :type errback: str or method
    :param dict meta: :attr:`~xpaw.http.HttpRequest.meta` 属性的初始值，用于存储请求相关的元信息
    :param render: 是否使用浏览器渲染

    .. attribute:: url

        URL地址

    .. attribute:: method

        HTTP method，``GET`` 、 ``POST`` 等

    .. attribute:: body

        请求发送的数据

    .. attribute:: headers

        HTTP headers

    .. attribute:: proxy

        代理地址

    .. attribute:: timeout

        请求超时时间

    .. attribute:: verify_ssl

        是否校验SSL

    .. attribute:: allow_redirects

        是否自动重定向

    .. attribute:: auth

        认证信息，用户名和密码

    .. attribute:: proxy_auth

        代理认证信息，用户名和密码

    .. attribute:: priority

        请求的优先级

    .. attribute:: dont_filter

        是否经过去重过滤器。xpaw会根据此属性决定该请求是否经过去重过滤器，如果经过去重过滤器，被认定为重复的请求会被忽略。

    .. attribute:: callback

        请求成功时的回调函数，必须是spider的成员函数，也可以传递递函数名称。

    .. attribute:: errback

        请求失败时的回调函数，必须是spider的成员函数，也可以传递函数名称。

    .. attribute:: meta

        只读属性，是一个 ``dict`` ，用于存储请求相关的元信息。
        用户可将自定义的元信息存储在 :attr:`~xpaw.http.HttpRequest.meta` 中。

    .. attribute:: render

        是否使用浏览器渲染

    .. method:: copy()

        复制request

    .. method:: replace(**kwargs)

        复制request并替换部分属性

.. class:: xpaw.http.HttpHeaders

    同 ``tornado.httputil.HTTPHeaders`` 。


Response API
------------

.. class:: xpaw.http.HttpResponse(url, status, body=None, headers=None, request=None, encoding=None)

    :param str url: URL地址
    :param int status: HTTP状态码
    :param bytes body: HTTP body
    :param headers: HTTP headers
    :type headers: dict or :class:`~xpaw.http.HttpHeaders`
    :param ~xpaw.http.HttpRequest request: 爬虫请求
    :param str encoding: HTTP body的编码格式

    .. attribute:: url

        URL地址，如果是xpaw生成的response则类型为 :class:`~xpaw.http.URL` 。

    .. attribute:: status

        HTTP状态码

    .. attribute:: body

        HTTP body

    .. attribute:: encoding

        指定HTTP body的编码，如果没有指定，则会根据response的header和body进行自动推断。

    .. attribute:: text

        只读属性，获取 :attr:`~xpaw.http.HttpResponse.body` 对应的文本内容，在没有设置 :attr:`~xpaw.http.HttpResponse.encoding` 的情况下会自动对编码进行推断。

    .. attribute:: headers

        HTTP headers，如果是xpaw生成的response则类型为 :class:`~xpaw.http.HttpHeaders` 。

    .. attribute:: request

        对应的 :class:`~xpaw.http.HttpRequest`

    .. attribute:: meta

        只读属性，即为对应的 :class:`~xpaw.http.HttpRequest` 的 :attr:`~xpaw.http.HttpRequest.meta` 属性。

    .. method:: copy()

        复制response。

    .. method:: replace(**kwargs)

        复制response并替换部分属性。
