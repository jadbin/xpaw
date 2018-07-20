.. _spider:

Spider
======

用户自定义的spider需要继承 :class:`xpaw.spider.Spider` ，并重写如下函数:

- :meth:`~xpaw.spider.Spider.start_requests` ：生成初始入口链接。
- :meth:`~xpaw.spider.Spider.parse` ：从爬取的网页中提取出所需的数据和后续待爬取的链接。
  该函数是默认处理 :class:`~xpaw.http.HttpResponse` 的函数，如果在每个生成的 :class:`~xpaw.http.HttpRequest` 中都通过 :attr:`~xpaw.http.HttpRequest.callback` 指定了相应的处理函数 ，也可以 **不重写** 该函数。


Spider API
----------

.. class:: xpaw.spider.Spider(config=None, **kwargs)

    用户自定义的spider需要继承此类。

    :param ~xpaw.config.Config config: 爬虫相关配置
    :param kwargs: 其他参数会作为爬虫的属性

    .. classmethod:: from_cluster(cluster)

        :param ~xpaw.cluster.LocalCluster cluster: cluster

        cluster通过该函数实例化spider，在该函数中会调用spider的构造器

    .. attribute:: config

        保存了爬虫相关的配置项，包括自定义配置项，参见 :class:`~xpaw.config.Config` 。

    .. attribute:: cluster

        通过cluster可以访问爬虫的各个组件，参见 :class:`~xpaw.cluster.LocalCluster` 。

    .. attribute:: logger

        提供纪录日志的logger。

    .. method:: log(message, *args, level=logging.INFO, **kwargs)

        通过logger纪录日志。

    .. method:: start_requests()

        生成初始请求

        :return: :class:`~xpaw.http.HttpRequest` 的可迭代对象。

    .. method:: parse(response)

        解析爬取结果

        :param ~xpaw.http.HttpResponse response: 爬取结果。

        :return: 可迭代对象，可以是新的请求 :class:`~xpaw.http.HttpRequest` ，和提取的数据 :class:`~xpaw.item.Item` 、 ``dict`` 等。

    .. method:: open()

        爬虫开始工作前会调用该函数。

    .. method:: close()

        爬虫完成工作时会调用该函数。

Cron Job
--------

可以使用 ``@every`` 实现定时任务，每隔设定的时间会重复执行被修饰的 ``start_requests`` 函数:

.. code-block:: python

    from xpaw import Spider, HttpRequest, Selector, every, run_spider


    class CronJobSpider(Spider):
        @every(seconds=10)
        def start_requests(self):
            yield HttpRequest("http://news.qq.com/", callback=self.parse, dont_filter=True)

        def parse(self, response):
            selector = Selector(response.text)
            major_news = selector.css("div.major a.linkto").text
            self.log("Major news:")
            for i in range(len(major_news)):
                self.log("%s: %s", i + 1, major_news[i])


    if __name__ == '__main__':
        run_spider(CronJobSpider, log_level='DEBUG')

``@every`` 可传入的参数:

- ``hours`` : 间隔的小时数

- ``minutes`` : 间隔的分钟数

- ``seconds`` : 间隔的秒数

注意需要通过参数 ``dont_filter=True`` 来设置request不经过去重过滤器，否则新产生的request会视为重复的请求。
