.. _usage:

Usage Guide
===========

Cron Job
--------

可以使用 ``xpaw.handler.every`` 实现定时任务，每隔设定的时间会重复执行修饰的函数:

.. code-block:: python

    from xpaw import Spider, HttpRequest, Selector
    from xpaw.handler import every
    from xpaw.run import run_spider


    class CronJobSpider(Spider):
        @every(seconds=10)
        def start_requests(self):
            yield HttpRequest("http://quotes.toscrape.com/", callback=self.parse, dont_filter=True)

        def parse(self, response):
            selector = Selector(response.text)
            tags = selector.css("div.tags-box a").text
            self.log("Top ten tags: %s", tags)


    if __name__ == '__main__':
        run_spider(CronJobSpider, log_level="DEBUG")

``@every`` 可传入的参数:

- ``hours`` : 间隔的小时数

- ``minutes`` : 间隔的分钟数

- ``seconds`` : 间隔的秒数

HttpRequest的参数 ``dont_filter=True`` 表示这个request不会经过去重过滤器。
