.. _core_api:

Core API
========


Cluster API
-----------

cluster是爬虫的调度者，实现对各个组件的控制和驱动。

.. class:: xpaw.cluster.LocalCluster(proj_dir=None, config=None)

    本地模式的cluster。

    :param str proj_dir: 爬虫工程的根目录。

    :param xpaw.config.BaseConfig config: 爬虫相关的配置项。


Config API
----------

.. class:: xpaw.config.Config(values=None)

    管理爬虫配置的类，继承了 :class:`~xpaw.config.BaseConfig` ，并设置了爬虫相关的默认配置项。

    爬虫相关的配置项参见 :ref:`settings` 。

.. class:: xpaw.config.BaseConfig(values=None)

    管理配置的类，参数 ``values`` 可以为 ``dict`` 或 :class:`~xpaw.config.BaseConfig` ，在实例化时会保存 ``values`` 中的配置。
