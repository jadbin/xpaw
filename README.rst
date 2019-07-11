====
xpaw
====

.. image:: https://travis-ci.org/jadbin/xpaw.svg?branch=master
    :target: https://travis-ci.org/jadbin/xpaw

.. image:: https://coveralls.io/repos/jadbin/xpaw/badge.svg?branch=master
    :target: https://coveralls.io/github/jadbin/xpaw?branch=master

.. image:: https://img.shields.io/badge/license-Apache 2-blue.svg
    :target: https://github.com/jadbin/xpaw/blob/master/LICENSE

Key Features
============

- A web scraping framework used to crawl web pages
- Data extraction tools used to extract structured data from web pages

Spider Example
==============

以下是我们的一个爬虫类示例，其作用为爬取 `百度新闻 <http://news.baidu.com/>`_ 的热点要闻:

.. code-block:: python

    from xpaw import Spider, HttpRequest, Selector, run_spider


    class BaiduNewsSpider(Spider):
        def start_requests(self):
            yield HttpRequest("http://news.baidu.com/", callback=self.parse)

        def parse(self, response):
            selector = Selector(response.text)
            hot = selector.css("div.hotnews a").text
            self.log("Hot News:")
            for i in range(len(hot)):
                self.log("%s: %s", i + 1, hot[i])


    if __name__ == '__main__':
        run_spider(BaiduNewsSpider)

在爬虫类中我们定义了一些方法：

- ``start_requests``: 返回爬虫初始请求。
- ``parse``: 处理请求得到的页面，这里借助 ``Selector`` 及CSS Selector语法提取到了我们所需的数据。

Documentation
=============

http://xpaw.readthedocs.io/
