.. _changelog:

Change log
==========

0.6.4 (2017-05-05)
------------------

Bug fixes
~~~~~~~~~

- HttpResponse中的 ``url`` 字段源于aiohttp返回的ClientResponse中的 ``url`` 字段，实际应为 ``URL`` 对象

Incompatible update
~~~~~~~~~~~~~~~~~~~

- LocalCluster启动时不再新建一个线程


0.6.3 (2017-05-01)
------------------

Incompatible update
~~~~~~~~~~~~~~~~~~~

- 优化日志工具中设置日志的接口


0.6.2 (2017-03-30)
------------------

New features
~~~~~~~~~~~~

- HttpResponse新增 ``encoding`` 和 ``text`` 字段，分别用于获取网页的编码及字符串形式的内容
- 新增ResponseMatchMiddleware，用于初步判断得到的页面是否符合要求
- 新增CookieJarMiddleware，用于维护请求过程中产生的cookie，同时HttpRequest的meta中新增系统项 ``cookie_jar`` 作为发起请求时使用的cookie jar
- HttpRequest的meta中新增系统项 ``timeout`` ，用于精确控制某个请求的超时时间
- 系统配置新增 ``queue_cls`` 项，用于替换默认的请求队列


0.6.1 (2017-03-23)
------------------

New features
~~~~~~~~~~~~

- 中间件添加open和close两个钩子函数，分别对应开启和关闭爬虫的事件
- RetryMiddleware中可以自定义需要重试的HTTP状态码
- 新增SpeedLimitMiddleware，用于爬虫限速
- 新增ProxyMiddleware，用于为请求添加指定代理

Incompatible update
~~~~~~~~~~~~~~~~~~~

- 移除MongoDedupeMiddleware及对pymongo的依赖
- 修改ProxyAgentMiddleware、RetryMiddleware在配置文件中的参数格式
- DepthMiddleware更名为MaxDepthMiddleware


0.6.0 (2017-03-16)
------------------

开始投入试用的第一个版本。
