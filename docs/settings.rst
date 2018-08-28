.. _settings:

Settings
========

爬虫相关配置项可以通过如下几种方式设定:

- **命令行** - 直接在命令行中设定的配置项。 ``run_spider`` 、 ``run_crawler`` 中传递的关键字参数同样视为命令行参数。
- **命令行配置文件** - 在命令行中通过参数 ``-c, --config`` 设定的配置文件中的配置项。
- **工程配置文件** - 在工程的配置文件 ``config.py`` 中设定的配置项。
- **默认配置** - 默认的配置项。

配置的优先级为： **命令行** > **命令行配置文件** > **工程配置文件** > **默认配置** ，对于同一配置项，高优先级的配置会覆盖低优先级的配置。

接下来我们会按类别依次给出爬虫相关的各个配置项。

Running
-------

.. _daemon:

daemon
^^^^^^

- ``-d, --daemon``
- Default: ``False``

是否在后台运行。

.. _pid_file:

pid_file
^^^^^^^^

- ``--pid-file``
- Default: ``None``

保存爬虫进程PID的文件。

Logging
-------

.. _log_level:

log_level
^^^^^^^^^

- ``-l, --log-level``
- Default: ``INFO``

日志级别，包括 ``DEBUG`` 、 ``INFO`` 、 ``WARNING`` 和 ``ERROR`` ，以及对应的小写形式。

.. _log_file:

log_file
^^^^^^^^

- ``--log-file``
- Default: ``None``

日志写入的文件。

Downloading
-----------

.. _downloader_clients:

downloader_clients
^^^^^^^^^^^^^^^^^^

- ``--downloader-clients``
- Default: ``100``

下载时的并发量。

.. _downloader_timeout:

downloader_timeout
^^^^^^^^^^^^^^^^^^

- ``--downloader-timeout``
- Default: ``20``

下载的超时时间（单位：秒）。

.. _verify_ssl:

verify_ssl
^^^^^^^^^^

- Default: ``False``

是否验证ssl证书。

.. _allow_redirects:

allow_redirects
^^^^^^^^^^^^^^^

- Default: ``True``

是否允许重定向。

.. _cookie_jar_enabled:

cookie_jar_enabled
^^^^^^^^^^^^^^^^^^

- ``--cookie-jar-enabled``
- Default: ``False``

是否启用cookies。

.. _default_headers:

default_headers
^^^^^^^^^^^^^^^

- Default::

    {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.8',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

默认添加的HTTP请求的header。

.. _user_agent:

user_agent
^^^^^^^^^^

- Default: ``:desktop``

指定HTTP请求头的User-Agent字段。

以 ``:`` 开头表示命令模式，命令分为终端类型和浏览器类型， 终端类型包括 ``desktop`` 、``mobile``，浏览器类型包括 ``chrome`` 。
多个命令之间用逗号 ``,`` 隔开，如 ``:mobile,chrome`` 表示移动端的Chrome浏览器。

其他字符串则直接视为User-Agent。

.. note::
    只有当 :ref:`default_headers` 中没有设置 ``User-Agent`` 时， :ref:`user_agent` 配置才会生效。

.. _random_user_agent:

random_user_agent
^^^^^^^^^^^^^^^^^

- Default: ``False``

随机设定HTTP请求头的User-Agent字段。

当 :ref:`user_agent` 为命令模式时，随机生成符合其约束的User-Agent；当 :ref:`user_agent` 为普通字符串时，则会覆盖其设置。

.. _imitating_proxy_enabled:

imitating_proxy_enabled
^^^^^^^^^^^^^^^^^^^^^^^

- Default: ``False``

模拟代理，设置HTTP请求头的Via和X-Forwarded-For字段。

.. _proxy:

proxy
^^^^^

- Default: ``None``

设置HTTP请求的代理，可以为单个代理，也可以为多个代理的list。

Retry
-----

.. _retry_enabled:

retry_enabled
^^^^^^^^^^^^^

- Default: ``True``

是否重试失败的HTTP请求。

.. _max_retry_times:

max_retry_times
^^^^^^^^^^^^^^^

- Default: ``3``

最大重试次数。

.. _retry_http_status:

retry_http_status
^^^^^^^^^^^^^^^^^

- Default: ``(500, 502, 503, 504, 408, 429)``

进行重试的HTTP状态码。

可以用 ``x`` 表示通配，例如 ``20x`` 表示 ``200`` 、 ``202`` 等所有 ``20`` 开头的状态码， ``4xx`` 表示所有 ``4`` 开头的状态码。

前面加 ``!`` 表示取反，例如 ``!2xx`` 表示所有不是以 ``2`` 开头的状态码。

Speed Limit
-----------

.. _speed_limit_enabled:

speed_limit_enabled
^^^^^^^^^^^^^^^^^^^

- Default: ``False``

是否开启限速。

.. _speed_limit_rate:

speed_limit_rate
^^^^^^^^^^^^^^^^

- Default: ``1``

下载速率，单位：请求/秒。

.. _speed_limit_burst:

speed_limit_burst
^^^^^^^^^^^^^^^^^

- Default: ``1``

下载时最大并发量。

Spider Behaviour
----------------

.. _max_depth:

max_depth
^^^^^^^^^

- Default: ``None``

爬虫的爬取的最大深度， ``None`` 表示没有限制。

Components
----------

.. _spider_setting:

spider
^^^^^^

- Default: ``None``

使用的爬虫类或爬虫类路径。

.. _downloader_middlewares_setting:

downloader_middlewares
^^^^^^^^^^^^^^^^^^^^^^

- Default: ``None``

使用的下载中间件。

.. _spider_middlewares_setting:

spider_middlewares
^^^^^^^^^^^^^^^^^^

- Default: ``None``

使用的解析中间件。

.. _item_pipelines_setting:

item_pipelines
^^^^^^^^^^^^^^

- Default: ``None``

使用的数据处理器。

.. _extensions_setting:

extensions
^^^^^^^^^^

- Default: ``None``

使用的拓展。
