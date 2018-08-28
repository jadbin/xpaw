.. _req_resp:

Request & Response
==================

我们通过 :class:`~xpaw.http.HttpRequest` 和 :class:`~xpaw.http.HttpResponse` 封装爬取的请求和对应的结果。

通常情况下， :class:`~xpaw.http.HttpRequest` 一部分来自于spider中 :meth:`~xpaw.spider.Spider.start_requests` 方法生成的初始请求，另一部分来自于 :meth:`~xpaw.spider.Spider.parse` 方法解析页面得到的新的请求。
针对每个 :class:`~xpaw.http.HttpRequest` ，如果请求成功xpaw会生成对应的 :class:`~xpaw.http.HttpResponse` ，一般无需我们自己去构造 :class:`~xpaw.http.HttpResponse` 。

Request API
-----------

.. class:: xpaw.http.HttpRequest(url, method="GET", body=None, params=None, headers=None, cookies=None, meta=None, priority=None, dont_filter=False, callback=None, errback=None)

    用户通过此类封装HTTP请求。

    :param url: URL地址
    :type url: str or yarl.URL
    :param str method: HTTP method，``GET`` 、 ``POST`` 等
    :param body: 请求发送的数据
    :type body: bytes or str or dict or aiohttp.FormData
    :param params: 请求参数
    :type params: dict or multidict.MultiDict
    :param headers: HTTP headers
    :type headers: dict or multidict.CIMultiDict
    :param cookies: cookies
    :type cookies: dict
    :param dict meta: :attr:`~xpaw.http.HttpRequest.meta` 属性的初始值，用于存储请求相关的元信息
    :param float priority: 请求的优先级
    :param bool dont_filter: 是否经过去重过滤器
    :param callback: 请求成功时的回调函数，必须是spider的成员函数，也可以传递递函数名称
    :type callback: str or method
    :param errback: 请求失败时的回调函数，必须是spider的成员函数，也可以传递函数名称
    :type errback: str or method

    .. attribute:: url

        URL地址

    .. attribute:: method

        HTTP method，``GET`` 、 ``POST`` 等

    .. attribute:: body

        请求发送的数据

    .. attribute:: params

        请求参数

    .. attribute:: headers

        HTTP headers

    .. attribute:: cookies

        cookies

    .. attribute:: meta

        只读属性，是一个 ``dict`` ，用于存储请求相关的元信息。
        xpaw预设各项元信息详见 :ref:`request_meta` 。
        用户可将自定义的元信息存储在 :attr:`~xpaw.http.HttpRequest.meta` 中。

    .. attribute:: priority

        请求的优先级

    .. attribute:: dont_filter

        是否经过去重过滤器。xpaw会根据此属性决定该请求是否经过去重过滤器，如果经过去重过滤器，被认定为重复的请求会被忽略。

    .. attribute:: callback

        请求成功时的回调函数，必须是spider的成员函数，也可以传递递函数名称。

    .. attribute:: errback

        请求失败时的回调函数，必须是spider的成员函数，也可以传递函数名称。

    .. method:: copy()

        复制request。

    .. method:: replace(**kwargs)

        复制request并替换部分属性。

.. _request_meta:

Request Meta Keys
-----------------

:class:`~xpaw.http.HttpRequest` 的 :attr:`~xpaw.http.HttpRequest.meta` 属性用于存储请求相关的元信息，其中xpaw预设的各项元信息如下：

- ``timeout`` : 可以通过设置 ``timeout`` 分别控制每个request的超时时间。

- ``verify_ssl`` : 是否校验SSL证书。

- ``allow_redirects`` : 是否允许重定向。

- ``auth`` : 设置request的HTTP Basic Auth，可以是 ``str`` 、 ``tuple`` 或 ``aiohttp.helpers.BasicAuth`` 。

- ``proxy`` : 设置请求使用的代理。

- ``proxy_auth`` : 设置代理的HTTP Basic Auth。

- ``cookie_jar`` : 设置请求相关的cookie jar。

- ``cookie_jar_key`` : 设置代表cookie jar的标识符。

- ``depth`` : 当使用 :class:`~xpaw.spidermws.DepthMiddleware` 时，纪录当前request的深度。

Response API
------------

.. class:: xpaw.http.HttpResponse(url, status, body=None, headers=None, cookies=None, request=None)

    :param url: URL地址
    :type url: str or yarl.URL
    :param int status: HTTP状态码
    :param bytes body: HTTP body
    :param headers: HTTP headers
    :type headers: dict or multidict.CIMultiDict
    :param cookies: cookies
    :type cookies: dict
    :param ~xpaw.http.HttpRequest request: 爬虫请求

    .. attribute:: url

        URL地址，如果是xpaw生成的response则类型为 ``yarl.URL`` 。

    .. attribute:: status

        HTTP状态码

    .. attribute:: body

        HTTP body

    .. attribute:: encoding

        指定HTTP body的编码，如果没有指定，则会根据response的header和body进行自动推断。

    .. attribute:: text

        只读属性，获取 :attr:`~xpaw.http.HttpResponse.body` 对应的文本内容，在没有设置 :attr:`~xpaw.http.HttpResponse.encoding` 的情况下会自动对编码进行推断。

    .. attribute:: headers

        HTTP headers，如果是xpaw生成的response则类型为 ``multidict.CIMultiDictProxy`` 。

    .. attribute:: cookies

        cookies

    .. attribute:: request

        对应的 :class:`~xpaw.http.HttpRequest`

    .. attribute:: meta

        只读属性，是 :class:`~xpaw.http.HttpRequest` 的 :attr:`~xpaw.http.HttpRequest.meta` 属性的映射。

    .. method:: copy()

        复制response。

    .. method:: replace(**kwargs)

        复制response并替换部分属性。
