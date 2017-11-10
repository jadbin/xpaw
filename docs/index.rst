.. xpaw documentation master file, created by
   sphinx-quickstart on Thu Mar 16 11:08:48 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

============================
xpaw |version| documentation
============================

Key Features
============

- Provides a web scraping framework used to crawl web pages.
- Provides data extraction tools used to extract structured data from web pages.

Installation
============

安装xpaw需要Python 3.5及更高版本的环境支持。

可以使用如下命令安装xpaw:

.. code-block:: bash

    $ pip install xpaw

如果安装过程中遇到lxml安装失败的情况，可参考 `lxml installation <http://lxml.de/installation.html>`_ 。

可以使用如下命令升级xpaw:

.. code-block:: bash

    $ pip install -U xpaw

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

Requirements
============

- `aiohttp`_
- `lxml`_
- `cssselect`_

.. _aiohttp: https://pypi.python.org/pypi/aiohttp
.. _lxml: https://pypi.python.org/pypi/lxml
.. _cssselect: https://pypi.python.org/pypi/cssselect

Getting Started
===============

.. toctree::
   :maxdepth: 2

   tutorial
   usage

All the Rest
============

.. toctree::
   :maxdepth: 1

   changelog
