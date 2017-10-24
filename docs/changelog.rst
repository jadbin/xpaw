.. _changelog:

Change log
==========

0.7.0 (2017-10-24)
------------------

New features
~~~~~~~~~~~~

- 使用继承Dupefilter的去重过滤器来实现去重功能，系统配置新增 ``dupefilter_cls`` 项，用于替换默认的去重过滤器
- ``xpaw.utils.run`` 模块中新增 ``run_crawler`` 函数，便于在python代码中控制开启爬虫

Update
~~~~~~

- 使用config.py替代config.yaml作为配置文件，移除对pyyaml的依赖
- ForwardedForMiddleware移动到 ``xpaw.downloadermws.headers`` 模块下
- 修改aiohttp的版本限制到>=2.2.0
- 更新了中间件的错误处理机制
- 不再采用中间件的形式实现请求的去重功能，并移除相关的中间件
- ProxyAgentMiddleware的 ``proxy_agnet`` 配置下面 ``addr`` 字段更名为 ``agent_addr``


0.6.5 (2017-05-09)
------------------

New features
~~~~~~~~~~~~

- HttpRequest新增 ``errback`` 字段，表示无法正常获取到HttpResponse时触发的函数

Bug fixes
~~~~~~~~~

- ResponseMatchMiddleware的配置修改为列表

Update
~~~~~~

- middleware的顺序修改为依次向downloader/spider靠近，层层包裹
- 移除任务配置中随机生成的 ``task_id``


0.6.4 (2017-05-05)
------------------

Bug fixes
~~~~~~~~~

- HttpResponse中的 ``url`` 字段源于aiohttp返回的ClientResponse中的 ``url`` 字段，实际应为 ``URL`` 对象

Update
~~~~~~

- LocalCluster启动时不再新建一个线程


0.6.3 (2017-05-01)
------------------

Update
~~~~~~

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

Update
~~~~~~

- 移除MongoDedupeMiddleware及对pymongo的依赖
- 修改ProxyAgentMiddleware、RetryMiddleware在配置文件中的参数格式
- DepthMiddleware更名为MaxDepthMiddleware


0.6.0 (2017-03-16)
------------------

开始投入试用的第一个版本。
