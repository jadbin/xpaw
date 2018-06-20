.. _spider:

Spider
======

用户自定义的spider需要继承 :class:`xpaw.spider.Spider` ，并重写如下函数:

- :meth:`~xpaw.spider.Spider.start_requests` ：生成初始入口链接。
- :meth:`~xpaw.spider.Spider.parse` ：从爬取的网页中提取出所需的数据和后续待爬取的链接。
  该函数是默认处理 :class:`~xpaw.http.HttpResponse` 的函数，如果在每个生成的 :class:`~xpaw.http.HttpRequest` 中都通过 :attr:`~xpaw.http.HttpRequest.callback` 指定了相应的处理函数 ，也可以 **不重写** 该函数。


Spider API
----------

.. class:: xpaw.spider.Spider(config=None, cluster=None)

    用户自定义的spider需要继承此类，如需重写 ``__init___`` 需保持参数一致。

    :param xpaw.config.Config config: 爬虫相关配置

    :param xpaw.cluster.LocalCluster cluster: cluster

    .. classmethod:: from_cluster(cluster)

        cluster通过该函数实例化spider，在该函数中会调用spider的构造器

        :param xpaw.cluster.LocalCluster cluster: cluster

    .. attribute:: cluster

        通过cluster可以访问爬虫的各个组件，参见 :class:`~xpaw.cluster.LocalCluster` 。

    .. attribute:: config

        保存了爬虫相关的配置项，包括自定义配置项，参见 :class:`~xpaw.config.Config` 。

    .. attribute:: logger

        提供纪录日志的logger。

    .. method:: log(message, *args, level=logging.INFO, **kwargs)

        通过logger纪录日志。

    .. method:: start_requests()

    .. method:: parse(response)

