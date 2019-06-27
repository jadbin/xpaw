.. _problems:

Specific Problems
=================

Cron Job
--------

可以使用 ``@every`` 实现定时任务，每隔设定的时间会重复执行被修饰的 ``start_requests`` 函数:

.. code-block:: python

    from xpaw import Spider, HttpRequest, Selector, every, run_spider


    class CronJobSpider(Spider):
        @every(seconds=10)
        def start_requests(self):
            yield HttpRequest("http://news.baidu.com/", callback=self.parse, dont_filter=True)

        def parse(self, response):
            selector = Selector(response.text)
            hot = selector.css("div.hotnews a").text
            self.log("Hot News:")
            for i in range(len(hot)):
                self.log("%s: %s", i + 1, hot[i])


    if __name__ == '__main__':
        run_spider(CronJobSpider)

``@every`` 可传入的参数:

- ``hours`` : 间隔的小时数

- ``minutes`` : 间隔的分钟数

- ``seconds`` : 间隔的秒数

注意需要通过参数 ``dont_filter=True`` 来设置 :class:`~xpaw.http.HttpRequest` 不经过去重过滤器，否则新产生的 :class:`~xpaw.http.HttpRequest` 会视为重复的请求。


Dynamic Webpages
----------------

一种解决方案是借助Chrome的调试工具找到动态内容请求的接口，然后在爬虫中直接从接口拿数据。

另一种方案是在 :class:`~xpaw.http.HttpRequest` 中设置 ``render=True`` ，则会默认使用Chrome浏览器对页面进行渲染。

.. code-block:: python

    from xpaw import Spider, HttpRequest, Selector, run_spider


    class RenderingSpider(Spider):
        def start_requests(self):
            yield HttpRequest('http://quotes.toscrape.com/js/', callback=self.parse, render=True)

        def parse(self, response):
            selector = Selector(response.text)
            for quote in selector.css('div.quote'):
                text = quote.css('span.text')[0].text
                author = quote.css('small.author')[0].text
                self.log(author + ": " + text)


    if __name__ == '__main__':
        run_spider(RenderingSpider)

.. note::

    如果需要使用渲染功能，则需要提前装好Chrome驱动。
