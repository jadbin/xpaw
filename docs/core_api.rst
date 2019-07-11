.. _core_api:

Core API
========

.. _crawler_api:

Crawler API
-----------

通常用户自定义的组件可以在class中定义类似如下的函数，来达到获取配置的目的：

.. code-block:: python

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.config)

对于用户自定义的组件，xpaw会首先检查是否存在名为 ``from_crawler`` 的函数，如果存在则会通过调用 ``from_crawler`` 来实例化对象:

.. code-block:: python

    foo = FooClass.from_crawler(crawler)

如果不存在该函数，则会调用默认的不含参数的构造器来实例化：

.. code-block:: python

    foo = FooClass()

对于spider来讲，由于强制要求继承 :class:`~xpaw.spider.Spider` 类，且在该类中已经实现了 ``from_crawler`` 函数，我们可以直接在spider中通过 ``self.config`` 来获取配置，通过 ``self.crawler`` 来获取crawler。

``from_crawler`` 提供了获取crawler的途径，通过crawler我们不仅可以获取到 :attr:`~xpaw.crawler.Crawler.config` ，也可以获取到其他的我们需要使用的crawler的属性。


.. class:: xpaw.crawler.Crawler(config)

    本地模式的crawler

    :param ~xpaw.config.Config config: 爬虫相关的配置项

    .. attribute:: config

    爬虫相关的配置项，对于 :attr:`~xpaw.crawler.Crawler.config` 的使用可以参考 :ref:`config_api` 。

.. _config_api:

Config API
----------

.. class:: xpaw.config.Config(__values=None, **kwargs)

    管理爬虫配置的类。

    .. method:: get(name, default=None)

        获取配置

        :param str name: 参数名称
        :param default: 缺省值

    .. method:: getbool(name, default=None)

        获取 ``bool`` 型参数，如果值不能转换为 ``bool`` 类型，返回 ``None`` 。

    .. method:: getint(name, default=None)

        获取 ``int`` 型参数，如果值不能转换为 ``int`` 类型，返回 ``None`` 。

    .. method:: getint(name, default=None)

        获取 ``float`` 型参数，如果值不能转换为 ``float`` 类型，返回 ``None`` 。

    .. method:: getlist(name, default=None)

        将参数值封装为 ``list`` 并返回。
        如果参数值是 ``str`` ，则会根据 ``,`` 分隔为多个参数值。

    .. method:: set(name, value):

        设置参数值

        :param str name: 参数名称
        :param value: 参数值

    .. method:: update(values):

        更新参数

        :param values: 新的参数
        :type values: dict or :class:`~xpaw.config.Config`

    .. method:: delete(name):

        删除参数

        :param name: 参数名称

    .. method:: copy()

        复制配置
