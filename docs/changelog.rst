.. _changelog:

Change log
==========

0.9.0 (2017-11-13)
------------------

New features
~~~~~~~~~~~~

- 中间件的加载细分为内置中间件和用户自定义中间件两部分，内置中间件自动加载，用户中间件的加载由配置项确定；
  中间件加载的顺序由配置的权值确定，权值越大越贴近downloader/spider
- 添加 ``xpaw.errors.NotEnabled`` ，在中间件/拓展的构造函数中控制抛出该异常来实现开启或禁用该中间件/拓展。
- 添加UserAgentMiddleware，支持选择PC端或移动端的User-Agent，支持随机User-Agent
- 支持配置日志写入指定文件

Bug fixes
~~~~~~~~~

- 修复了request的fingerprint计算时没有考虑端口号的bug

Update
~~~~~~

- 移除ResponseNotMatchMiddleware
- 移除ProxyAgentMiddle，原有功能并入ProxyMiddleware
- 中间件的参数配置扁平化，修改了RetryMiddleware、ProxyMiddleware、DepthMiddleware的参数配置方式
- ForwardedForMiddleware更名为ImitatingProxyMiddleware，新增添加 ``Via`` 请求头的功能
- 系统配置 ``downloader_verify_ssl`` 更名为 ``verify_ssl`` ， ``downloader_cookie_jar_enabled`` 更名为 ``cookie_jar_enabled``
- 更新了downloader和spider相关的错误处理流程
- 更新了判定job结束的逻辑


0.8.0 (2017-11-5)
-----------------

New features
~~~~~~~~~~~~

- spider的 ``start_requests`` 和 ``parse`` 函数支持async类型和python 3.6中的async generator类型
- spider中间件的handle_*函数支持async类型
- 添加事件驱动相关的eventbus和events模块，支持事件的订阅、发送，可通过 ``cluster.event_bus`` 获取event bus组件
- 捕获SIGINT和SIGTERM信号并做出相应处理
- 添加extension模块，支持用户自定义拓展
- 添加statscenter模块，用于收集、管理系统产生的各项统计量，可通过 ``cluster.stats_center`` 获取stats center组件；
  系统配置添加 ``stats_center_cls`` 项，用于替换默认的stats center的实现
- SetDupeFilter添加 ``clear`` 函数
- 系统配置添加 ``downloader_verify_ssl`` 项，用于开启或关闭SSL证书认证
- HttpRequest的 ``body`` 参数支持bytes、str、FormData、dict (json)等形式
- HttpRequest添加 ``params`` , ``auth`` , ``proxy_auth`` , ``priority`` 等属性
- 添加深度优先队列LifoQueue，以及优先级队列PriorityQueue，默认 ``queue_cls`` 更改为 ``xpaw.queue.PriorityQueue``
- 支持设定HTTP请求的优先级并按优先级进行爬取
- 添加item、pipeline模块，支持spider在处理response时返回BaseItem的实例或dict，并交由用户自定义的item pipelines进行处理

Update
~~~~~~

- 实例化中间件的classmethod ``from_config`` 更改为 ``from_cluster`` ，现在 ``config`` 参数可以通过 ``cluster.config`` 获取
- queue组件的 ``push`` , ``pop`` 函数，以及dupefilter组件的 ``is_duplicated`` 函数改为async类型
- 移除queue组件和dupefilter组件的基类，RequestDequeue更名为FifoQueue
- 系统不再默认调用dupefilter组件和queue组件的 ``open`` 和 ``close`` 函数，如果自定义的组件包含这些函数，可通过订阅相关事件的方式进行调用
- 系统配置 ``dupefilter_cls`` 更名为 ``dupe_filter_cls`` ，cluster的 ``dupefilter`` 属性更名为 ``dupe_filter``
- RequestHeadersMiddleware更改为DefaultHeadersMiddleware，配置字段 ``request_headers`` 更改为 ``default_headers``，功能由覆盖headers变为设置默认的headers
- 修改了MaxDepthMiddleware更改为DepthMiddleware的参数配置方式，功能变为记录request的depth并对max depth加以限制
- 修改了ProxyMiddleware和ProxyAgentMiddleware的参数配置方式
- 移除CookieJarMiddleware，通过 ``downloader_cookie_jar_enabled`` 配置是否启用cookie
- 重写了SpeedLimitMiddleware，通过 ``rate`` (采集速率) 和 ``burst`` (最大并发数) 来限制采集速率
- 更新了 ``request_fingerprint`` 的计算方式
- 修改aiohttp的版本限制为>=2.3.2


0.7.1 (2017-10-25)
------------------

New features
~~~~~~~~~~~~

- 通过 ``xpaw.handler.every`` 实现定时任务功能
- HttpRequest添加 ``dont_filter`` 字段，为 ``True`` 时表示该请求不会被过滤
- ``xpaw.run`` 模块中添加 ``run_spider`` 函数，便于在python代码中直接运行Spider类

Update
~~~~~~

- ``xpaw.utils.run`` 模块中 ``run_crawler`` 函数移动至 ``xpaw.run`` 模块
- 原utils, commands, downloadersmws, spidermws各合并为一个模块


0.7.0 (2017-10-24)
------------------

New features
~~~~~~~~~~~~

- 使用继承Dupefilter的去重过滤器来实现去重功能，系统配置添加 ``dupefilter_cls`` 项，用于替换默认的去重过滤器
- ``xpaw.utils.run`` 模块中添加 ``run_crawler`` 函数，便于在python代码中控制开启爬虫

Update
~~~~~~

- 使用config.py替代config.yaml作为配置文件，移除对pyyaml的依赖
- ForwardedForMiddleware移动到 ``xpaw.downloadermws.headers`` 模块下
- 修改aiohttp的版本限制为>=2.2.0
- 更新了downloader和spider相关的错误处理流程
- 不再采用中间件的形式实现请求的去重功能，并移除相关的中间件
- ProxyAgentMiddleware的 ``proxy_agnet`` 配置下面 ``addr`` 字段更名为 ``agent_addr``


0.6.5 (2017-05-09)
------------------

New features
~~~~~~~~~~~~

- HttpRequest添加 ``errback`` 字段，表示无法正常获取到HttpResponse时触发的函数

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

- HttpResponse添加 ``encoding`` 和 ``text`` 字段，分别用于获取网页的编码及字符串形式的内容
- 添加ResponseMatchMiddleware，用于初步判断得到的页面是否符合要求
- 添加CookieJarMiddleware，用于维护请求过程中产生的cookie，同时HttpRequest的meta中添加系统项 ``cookie_jar`` 作为发起请求时使用的cookie jar
- HttpRequest的meta中添加系统项 ``timeout`` ，用于精确控制某个请求的超时时间
- 系统配置添加 ``queue_cls`` 项，用于替换默认的请求队列


0.6.1 (2017-03-23)
------------------

New features
~~~~~~~~~~~~

- 中间件添加 ``open`` 和 ``close`` 两个钩子函数，分别对应开启和关闭爬虫的事件
- RetryMiddleware中可以自定义需要重试的HTTP状态码
- 添加SpeedLimitMiddleware，用于爬虫限速
- 添加ProxyMiddleware，用于为请求添加指定代理

Update
~~~~~~

- 移除MongoDedupeMiddleware及对pymongo的依赖
- 修改ProxyAgentMiddleware、RetryMiddleware在配置文件中的参数格式
- DepthMiddleware更名为MaxDepthMiddleware


0.6.0 (2017-03-16)
------------------

开始投入试用的第一个版本。
