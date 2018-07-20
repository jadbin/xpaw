.. include:: <isonum.txt>

.. _tutorial2:

Tutorial II: Spider Project
===========================

在这里我们将展示以工程的形式构建爬虫的流程，工程的完整代码位于 `examples/quotes <https://github.com/jadbin/xpaw/tree/master/examples/quotes>`_ 。

同 :ref:`tutorial1` 一样，我们的爬取 `quotes.toscrape.com <http://quotes.toscrape.com/>`_ 网站中所有的quotes并以json的形式保存下来，每个quote包含如下几个字段:

============  ======================
名称            含义
============  ======================
text           quote的内容
author         quote作者
author_url     作者的相关链接
tags           quote的标签列表
============  ======================

Creating our Project
--------------------

执行工程初始化命令::

    $ xpaw init quotes

其中 ``quotes`` 为工程名称，也可为具体的路径。

工程的目录结构如下::

    quotes/                   # 工程根目录
        config.py             # 工程的配置文件
        quotes/               # 工程的Python模块目录，在该目录下编写Python代码
            __init__.py
            items.py          # 默认生成的数据类型模块
            pipelines.py      # 默认生成的数据处理模块
            spider.py         # 默认生成的爬虫模块

其中config.py包含了整个工程的相关配置，也是工程运行时的入口文件，具体的配置项可参考 :ref:`settings` 。

Definition of Data Fields
-------------------------

我们在items.py中定义我们需要的数据的各个字段:

.. code-block:: python

    from xpaw import Item, Field


    class QuotesItem(Item):
        text = Field()
        author = Field()
        author_url = Field()
        tags = Field()

我们编写的item需要继承 ``xpaw.Item`` 类，item的各个字段利用 ``xpaw.Field`` 定义。

接下来我们会用QuotesItem来封装我们爬取到的quote数据。

Writing our Spider
------------------

我们沿用 :ref:`tutorial1` 中的爬取逻辑，因此spider的代码几乎是一样的，不过这里我们用item来封装我们爬取到的quote数据:

.. code-block:: python

    from urllib.parse import urljoin

    from xpaw import Spider, HttpRequest, Selector

    from .items import QuotesItem


    class QuotesSpider(Spider):
        def start_requests(self):
            yield HttpRequest('http://quotes.toscrape.com/', callback=self.parse)

        def parse(self, response):
            selector = Selector(response.text)
            for quote in selector.css('div.quote'):
                text = quote.css('span.text')[0].text
                author = quote.css('small.author')[0].text
                author_url = quote.css('small+a')[0].attr('href')
                author_url = urljoin(str(response.url), author_url)
                tags = quote.css('div.tags a').text
                yield QuotesItem(text=text, tags=tags,
                                 author=author, author_url=author_url)
            next_page = selector.css('li.next a')
            if len(next_page) > 0:
                next_page_url = urljoin(str(response.url), next_page[0].attr('href'))
                yield HttpRequest(next_page_url, callback=self.parse)

这里我们的spider只负责数据和链接的抽取，对item的进一步处理则交由pipeline完成。

Storing the Scraped Data
------------------------

我们在pipelines.py中编写相应的pipeline来实现对item的处理:

.. code-block:: python

    import json
    from os.path import dirname, join

    home_dir = dirname(dirname(__file__))


    class QuotesPipeline:
        def __init__(self):
            self.data = []

        def handle_item(self, item):
            self.data.append(dict(item))

        def close(self):
            with open(join(home_dir, 'quotes.json'), 'w') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)

对于spider生成的item，xpaw会调用pipeline的 ``handle_item`` 函数对其进行处理，我们在该函数中将数据暂存到一个list中。
当爬取工作完成后，xpaw会调用pipeline的 ``close`` 函数 (如果存在的话)，我们借机在该函数中将所有爬取到的数据以json的格式写入到文件中。

在pipeline中适合进行数据清洗、存储等相关工作。

Running our Project
-------------------

进入到工程的根目录，运行如下命令::

    $ xpaw crawl ./ -l DEBUG

其中 ``crawl`` 的参数为工程的根目录的路径， ``-l DEBUG`` 设定了日志的级别为DEBUG。

运行结束之后，我们可以打开工程的根目录下的quotes.json的文件查看爬取到的数据。
