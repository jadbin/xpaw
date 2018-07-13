.. _core_api:

Core API
========

.. _cluster_api:

Cluster API
-----------

通常用户自定义的组件可以在class中定义类似如下的函数，来达到获取配置的目的：

.. code-block:: python

    @classmethod
    def from_cluster(cls, cluster):
        return cls(cluster.config)

对于用户自定义的组件，xpaw会首先检查是否存在名为 ``from_cluster`` 的函数，如果存在则会通过调用 ``from_cluster`` 来实例化对象:

.. code-block:: python

    foo = FooClass.from_cluster(cluster)

如果不存在该函数，则会调用默认的不含参数的构造器来实例化：

.. code-block:: python

    foo = FooClass()

对于spider来讲，由于强制要求继承 :class:`~xpaw.spider.Spider` 类，且在该类中已经实现了 ``from_cluster`` 函数，我们可以直接在spider中通过 ``self.config`` 来获取配置，通过 ``self.cluster`` 来获取cluster。

``from_cluster`` 提供了获取cluster的途径，通过cluster我们不仅可以获取到 :attr:`~xpaw.cluster.LocalCluster.config` ，也可以获取到其他的我们需要使用的cluster的属性。


.. class:: xpaw.cluster.LocalCluster(config)

    本地模式的cluster。

    :param ~xpaw.config.Config config: 爬虫相关的配置项。

    .. attribute:: config

    爬虫相关的配置项，对于 :attr:`~xpaw.cluster.LocalCluster.config` 的使用可以参考 :ref:`config_api` 。


.. _config_api:

Config API
----------

.. class:: xpaw.config.Config(values=None)

    管理爬虫配置的类，继承了 :class:`~xpaw.config.BaseConfig` ，并设置了爬虫相关的默认配置项。

    爬虫相关的默认配置项参见 :ref:`settings` 。

    :param values: 需要更新的配置项
    :type values: dict or :class:`~xpaw.config.BaseConfig`


.. class:: xpaw.config.BaseConfig(values=None)

    管理配置的类，参数 ``values`` 可以为 ``dict`` 或 :class:`~xpaw.config.BaseConfig` ，在实例化时会保存 ``values`` 中的配置。

    :param values: 需要更新的配置项
    :type values: dict or :class:`~xpaw.config.BaseConfig`
