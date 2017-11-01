.. _tutorial:

========
Tutorial
========

在这个tutorial中，我们的爬取目标为: `quotes.toscrape.com <http://quotes.toscrape.com/>`_ ，在此特别感谢 `scrapinghub <https://scrapinghub.com>`_ 提供了这个测试爬虫的网站。

我们的需求为爬取网站中所有的quotes并以json的形式保存下来，每个quote包含如下几个字段:

============  ======================
名称            含义
============  ======================
text           quote的内容
author         quote作者
author_url     作者的相关链接
tags           quote的标签列表
============  ======================

例如对于这个quote:

.. image:: /_static/quote_sample.png

我们得到的json数据为::

    {
        "text": "“I have not failed. I've just found 10,000 ways that won't work.”",
        "author": "Thomas A. Edison",
        "author_url": "http://quotes.toscrape.com/author/Thomas-A-Edison",
        "tags": ["edison", "failure", "inspirational", "paraphrased"]
    }

接下来我们会以project的形式构建爬虫，完整代码位于 `demos/quotes <https://github.com/jadbin/xpaw/tree/master/demos/quotes>`_ 中。

Creating our Project
====================

执行工程初始化命令::

    $ xpaw init quotes

其中 ``quotes`` 为工程名称，也可为具体的路径。

工程的目录结构如下::

    quotes/                   # 工程根目录
        setup.cfg             # 部署的配置文件
        quotes/               # 工程的Python模块目录，在该目录下编写Python代码
            __init__.py
            config.py         # 工程的配置文件
            items.py          # 默认生成的数据类型模块
            pipelines.py      # 默认生成的数据处理模块
            spider.py         # 默认生成的爬虫模块

Creating our Item
=================

我们在items.py中定义我们需要的数据的格式:

.. code-block:: python

    from xpaw import Item, Field


    class QuotesItem(Item):
        text = Field()
        author = Field()
        author_url = Field()
        tags = Field()

我们编写的item需要继承 ``xpaw.Item`` 类，item的各个字段利用 ``xpaw.Field`` 定义。

后续我们会用QuotesItem来封装我们爬取到的quote数据。

Creating our Spider
===================

我们编写的spider需要继承 ``xpaw.Spider`` 类，需要实现的功能包括:

- 生成初始入口链接
- 从爬取的网页中提取出所需的数据和后续待爬取的链接

.. code-block:: python

    from urllib.parse import urljoin

    from xpaw import Spider, HttpRequest, Selector

    from .items import QuotesItem


    class QuotesSpider(Spider):
        def start_requests(self):
            yield HttpRequest('http://quotes.toscrape.com/', callback=self.parse)

        def parse(self, response):
            selector = Selector(response.text)
            for subselector in selector.xpath('//div[@class="quote"]'):
                text = subselector.xpath('.//span[@itemprop="text"]')[0].text
                author = subselector.xpath('.//small[@itemprop="author"]')[0].text
                author_url = subselector.xpath('.//span/a/@href')[0].text
                author_url = urljoin(str(response.url), author_url)
                tags = subselector.xpath('.//div[class="tags"]/a').text
                yield QuotesItem(text=text, tags=tags,
                                 author=author, author_url=author_url)
            next_page = selector.xpath('//li[@class="next"]/a/@href')
            if len(next_page) > 0:
                next_page_url = urljoin(str(response.txt), next_page[0].text)
                yield HttpRequest(next_page_url, callback=self.parse)

我们需要在 ``start_requests`` 函数中生成入口链接，在这个任务中入口链接选择网站的首页即可。
HttpRequest的 ``callback`` 用来指定该request对应的response由哪个函数来处理。

.. note::

    - ``start_requests`` 函数的返回值需为可迭代对象，如tupe, list, generator等。
    - ``callback`` 只能指定为spider自身的成员函数

How to Run our Spider
=====================

首先进入到工程的根目录，然后执行如下命令::

    $ xpaw crawl ./

``crawl`` 命令的参数为工程的根目录的路径。

