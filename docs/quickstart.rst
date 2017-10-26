.. _quickstart:

===========
Quick Start
===========

Building a Spider Project
=========================

Creating a Project
------------------

执行工程初始化命令:

.. code-block:: bash

    $ xpaw init tutorial

其中 ``tutorial`` 为工程名称，也可为具体的路径。

工程目录具有如下的结构::

    tutorial/
        setup.cfg             # 部署配置文件
        tutorial/             # 工程的Python模块目录，在该目录下编写Python代码
            __init__.py
            config.py         # 工程配置文件
            spider.py         # 默认生成的爬虫文件

Creating a Spider
-----------------

我们编写的spider需要继承 ``xpaw.Spider`` 类，其承担的功能主要为:

* 定义初始待爬取的链接

* 从爬取的网页中提取出后续待爬取的链接

* 解析并存储网页中所需的数据

以下是我们的一个爬虫类示例，其作用为爬取 `腾讯新闻 <http://news.qq.com/>`_ 首页的"要闻"，可以直接将其复制到 ``tutorial/spider.py`` 中使用:

.. code-block:: python

    from xpaw import Spider, HttpRequest, Selector


    class TutorialSpider(Spider):
        def start_requests(self):
            yield HttpRequest("http://news.qq.com", callback=self.parse)

        def parse(self, response):
            selector = Selector(response.text)
            major_news = selector.xpath("//div[@class='item major']//a[@class='linkto']").text
            self.log("Major news:")
            for i in range(len(major_news)):
                self.log("{}: {}".format(i + 1, major_news[i]))

在爬虫类中我们定义了一些方法：

* ``start_requests``: 返回爬虫初始请求，返回值为 ``HttpRequest`` 的一个可迭代对象（列表、元组、生成器均可）。

* ``parse``: 处理请求得到的页面，这里借助 ``Selector`` 及XPath语法提取到了我们所需的数据。

  ``parse`` 函数同时可以返回新的请求，返回值可以为 ``None`` 或一个 ``HttpRequest`` 的可迭代对象。


.. note:: ``HttpRequest`` 的 ``callback`` 参数可以指定该请求对应的 ``HttpResponse`` 由哪个函数处理，且这个函数必须是我们的爬虫类的成员函数。如果 ``HttpRequest`` 没有指定 ``callback`` ，则由爬虫类默认的 ``parse`` 函数处理。

How to run our Spider
---------------------

首先进入到工程的根目录，然后执行如下命令:

.. code-block:: bash

    $ xpaw crawl ./

``crawl`` 命令的参数实际上为工程的根目录的路径。

如果需要在后台运行程序，可以借助 ``nohup`` 命令:

.. code-block:: bash

    $ nohup xpaw crawl ./ &

这样日志将会记录在当前目录下的 ``nohup.out`` 文件中。

更多 ``nohup`` 命令的使用细节请参阅其他资料。


How to Run a Single Spider
==========================

我们也可以直接编写spider类并运行:

.. code-block:: python

    # coding=utf-8

    from xpaw import Spider, HttpRequest, Selector
    from xpaw.run import run_spider


    class TutorialSpider(Spider):
        def start_requests(self):
            yield HttpRequest("http://news.qq.com", callback=self.parse)

        def parse(self, response):
            selector = Selector(response.text)
            major_news = selector.xpath("//div[@class='item major']//a[@class='linkto']").text
            self.log("Major news:")
            for i in range(len(major_news)):
                self.log("{}: {}".format(i + 1, major_news[i]))


    if __name__ == '__main__':
        run_spider(TutorialSpider, log_level="DEBUG")

