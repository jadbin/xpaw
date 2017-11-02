.. _tutorial:

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
--------------------

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

后续我们会用QuotesItem来封装我们爬取到的quote数据。

Writing our Spider
------------------

我们想到的一个可行的爬取思路为：从网站首页进入，然后不停地点击下一页，并且将浏览到的每个页面的上quote提取出来并保存。
接下来我们在spider.py中编写spider来实现我们的爬取思路。

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
            for quote in selector.xpath('//div[@class="quote"]'):
                text = quote.xpath('.//span[@itemprop="text"]')[0].text
                author = quote.xpath('.//small[@itemprop="author"]')[0].text
                author_url = quote.xpath('.//span/a/@href')[0].text
                author_url = urljoin(str(response.url), author_url)
                tags = quote.xpath('.//div[@class="tags"]/a').text
                yield QuotesItem(text=text, tags=tags,
                                 author=author, author_url=author_url)
            next_page = selector.xpath('//li[@class="next"]/a/@href')
            if len(next_page) > 0:
                next_page_url = urljoin(str(response.url), next_page[0].text)
                yield HttpRequest(next_page_url, callback=self.parse)

接下来将逐一解释我们的spider都做了那些事情。

Generation of start requests
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

xpaw在加载spider时会调用 ``start_requests`` 成员函数来获取整个爬取过程的入口链接，我们需要在该函数中生成入口链接并用HttpRequest进行封装。
在这个任务中入口链接选择网站的首页即可。
HttpRequest的 ``callback`` 用来指定该request对应的response由哪个函数来处理。

.. note::

    - ``start_requests`` 函数的返回值需为可迭代对象，如tupe, list, generator等。
    - ``callback`` 只能指定为spider自身的成员函数。

Extracting data
^^^^^^^^^^^^^^^

xpaw成功获取到response之后，会调用在request中指定的 ``callback`` 函数来处理response；
如果没有指定则会默认调用spider中名为 "parse" 的函数，这时如果没有定义 "parse" 函数，则会抛出异常。

我们之前指定了 ``parse`` 函数来处理response。
在 ``parse`` 函数中，我们借助xpaw内置的selector和XPath语句来完成数据的提取。
XPath提供了一套语法来定位XML树状结构中的节点、属性、文本等信息，有关XPath的详细信息可以参考 `XPath Tutorial <https://www.w3schools.com/xml/xpath_intro.asp>`_ 。

通过查看网页的源码，我们可以归纳出待提取的数据所在的节点的特征并用XPath语言对其描述，然后借助selector的相关接口来提取我们想要的数据。

.. note::

    spider中处理response的函数的返回值需为可迭代对象，如tupe, list, generator等。

Extracting links
^^^^^^^^^^^^^^^^

在 ``parse`` 函数中，我们还需要提取出翻页的链接来告诉xpaw还需要继续爬取哪些网页。

同样的，通过查看网页的源码，我们可以归纳出"下一页"所在的节点的特征并用XPath语言对其描述，然后借助selector的相关接口提取"下一页"的链接。
同 ``start_requests`` 一样，我们需要用HttpRequest封装提取的链接，并指定response继续由 ``parse`` 函数来处理。

.. note::

    在提取链接时我们不需要关注提取出URL是否重复了，xpaw会自动帮我们完成URL去重的工作。

Storing the Scraped Data
------------------------

我们在pipelines.py中编写pipeline来实现数据存储的逻辑:

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

对于spider生成的item，xpaw会调用pipeline的 ``handle_item`` 成员函数对其进行处理，我们在该函数中将数据暂存到一个list中。
当爬取工作完成后，xpaw会调用pipeline的 ``close`` 成员函数 (如果存在的话)，我们借机在该函数中将所有爬取到的数据以json的格式写入到文件中。

其实我们也可以选择在spider的 ``close`` 成员函数中完成数据的存储，这样甚至不用定义item和pipeline。
但是我们更推荐在pipeline中完成数据的存储，这样可以更方便地使用xpaw提供的一些功能。
关于xpaw提供的各项功能我们会在后续的章节中进行介绍。

How to Run our Project
----------------------

进入到工程的根目录，运行如下命令::

    $ xpaw crawl ./ -l DEBUG

其中``crawl`` 的参数为工程的根目录的路径， ``-l DEBUG`` 设定了日志的级别为DEBUG。

我们将会看到类似这样的日志::

    ...
    2017-11-02 13:40:46 xpaw.cluster [INFO]: Cluster is running
    2017-11-02 13:40:46 xpaw.cluster [DEBUG]: The request (url=http://quotes.toscrape.com/) has been pulled by coro[0]
    2017-11-02 13:40:46 xpaw.downloader [DEBUG]: HTTP request: GET http://quotes.toscrape.com/
    2017-11-02 13:40:46 xpaw.downloader [DEBUG]: HTTP response: http://quotes.toscrape.com/ 200
    2017-11-02 13:40:46 xpaw.pipeline [DEBUG]: Item (QuotesItem): {'text': '“The world as we have created it is a process of our thinking. It cannot be changed without changing our thinking.”', 'tags': ['change', 'deep-thoughts', 'thinking', 'world'], 'author': 'Albert Einstein', 'author_url': 'http://quotes.toscrape.com/author/Albert-Einstein'}
    ...
    2017-11-02 13:40:52 xpaw.pipeline [DEBUG]: Item (QuotesItem): {'text': '“... a mind needs books as a sword needs a whetstone, if it is to keep its edge.”', 'tags': ['books', 'mind'], 'author': 'George R.R. Martin', 'author_url': 'http://quotes.toscrape.com/author/George-R-R-Martin'}
    2017-11-02 13:41:36 xpaw.cluster [INFO]: Shutdown now
    2017-11-02 13:41:36 xpaw.cluster [INFO]: Cluster is stopped
    ...

运行结束之后，我们可以打开工程的根目录下的quotes.json的文件查看爬取到的数据。
