====
xpaw
====

.. image:: https://travis-ci.org/jadbin/xpaw.svg?branch=master
    :target: https://travis-ci.org/jadbin/xpaw

.. image:: https://coveralls.io/repos/jadbin/xpaw/badge.svg?branch=master&service=github
    :target: https://coveralls.io/github/jadbin/xpaw?branch=master

.. image:: https://img.shields.io/badge/license-Apache 2-blue.svg
    :target: https://github.com/jadbin/xpaw/blob/master/LICENSE

Key Features
============

- Provides a web scraping framework used to crawl web pages.
- Provides data extraction tools used to extract structured data from web pages.

Spider Example
==============

以下是我们的一个爬虫类示例，其作用为爬取 `腾讯新闻 <http://news.qq.com/>`_ 首页的"要闻":

.. code-block:: python

    from xpaw import Spider, HttpRequest, Selector
    from xpaw.run import run_spider


    class TencentNewsSpider(Spider):
        def start_requests(self):
            yield HttpRequest("http://news.qq.com/", callback=self.parse)

        def parse(self, response):
            selector = Selector(response.text)
            major_news = selector.css("div.major a.linkto").text
            self.log("Major news:")
            for i in range(len(major_news)):
                self.log("%s: %s", i + 1, major_news[i])


    if __name__ == '__main__':
        run_spider(TencentNewsSpider, log_level="DEBUG")

在爬虫类中我们定义了一些方法：

- ``start_requests``: 返回爬虫初始请求。
- ``parse``: 处理请求得到的页面，这里借助 ``Selector`` 及CSS Selector语法提取到了我们所需的数据。

Documentation
=============

http://xpaw.readthedocs.io/

Requirements
============

- Python >= 3.5
- `aiohttp`_
- `lxml`_
- `cssselect`_

.. _aiohttp: https://pypi.python.org/pypi/aiohttp
.. _lxml: https://pypi.python.org/pypi/lxml
.. _cssselect: https://pypi.python.org/pypi/cssselect
