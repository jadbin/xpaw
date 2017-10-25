.. _usage:

===========
Usage Guide
===========

Cron Job
========

可以使用 ``xpaw.handler.every`` 实现定时任务，每隔设定的时间会重复执行修饰的函数:

.. code-block:: python

    # coding=utf-8

    from xpaw import Spider, HttpRequest, Selector
    from xpaw.handler import every
    from xpaw.run import run_spider


    class CronJobSpider(Spider):
        def __init__(self, config):
            super().__init__(config)

        @every(seconds=10)
        def start_requests(self):
            yield HttpRequest("http://news.qq.com", callback=self.parse, dont_filter=True)

        def parse(self, response):
            selector = Selector(response.text)
            major_news = selector.xpath("//div[@class='item major']//a[@class='linkto']").text
            self.log("Major news:")
            for i in range(len(major_news)):
                self.log("{}: {}".format(i + 1, major_news[i]))


    if __name__ == '__main__':
        run_spider(CronJobSpider, log_level="DEBUG")

``@every`` 可传入的参数:

- ``hours`` : 间隔的小时数

- ``minutes`` : 间隔的分钟数

- ``seconds`` : 间隔的秒数

``@every`` 只能用于修饰Spider的 ``start_requests`` 成员函数。
