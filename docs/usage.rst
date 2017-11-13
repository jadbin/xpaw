.. _usage:

Usage Examples
==============

Running Single Spider
---------------------

如果爬取任务相对较为简单，我们也可以选择只编写spider，并借助 ``run_spider`` 直接运行爬虫：

.. code-block:: python

    from xpaw import Spider, HttpRequest, Selector
    from xpaw.run import run_spider


    class RunningSingleSpider(Spider):
        def start_requests(self):
            yield HttpRequest("http://quotes.toscrape.com/", callback=self.parse)

        def parse(self, response):
            selector = Selector(response.text)
            tags = selector.css("div.tags-box a").text
            self.log("Top ten tags: %s", tags)


    if __name__ == '__main__':
        run_spider(RunningSingleSpider, log_level="DEBUG")


Cron Job
--------

可以使用 ``@every`` 实现定时任务，每隔设定的时间会重复执行被修饰的 ``start_requests`` 函数:

.. code-block:: python

    from xpaw import Spider, HttpRequest, Selector, every
    from xpaw.run import run_spider


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
        run_spider(CronJobSpider, log_level="DEBUG")

``@every`` 可传入的参数:

- ``hours`` : 间隔的小时数

- ``minutes`` : 间隔的分钟数

- ``seconds`` : 间隔的秒数

HttpRequest的参数 ``dont_filter=True`` 表示这个request不会经过去重过滤器。
