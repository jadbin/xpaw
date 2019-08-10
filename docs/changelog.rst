.. _changelog:

Changelog
=========

0.12.0 (2019-08-10)
-------------------

- 移除爬虫工程初始化相关功能，推荐使用单文件spider或指定爬虫启动脚本
- 统一middleware、pipeline、extension等概念，统一由 ``extensions`` 配置爬虫的拓展

0.11.2 (2019-08-06)
-------------------

- 重构Chrome渲染器，由每次新建Chrome进程变为维护每个Chrome进程的tab
- 添加 ``chrome_renderer_options`` 配置项，实现同时运行多个具有不同设置的Chrome渲染器
- 修复爬虫工程的配置模版

0.11.1 (2019-07-29)
-------------------

- 移除 ``HttpRequest`` 中的 ``params`` 属性，但在构建 ``HttpRequest`` 时依然可以传入 ``params``

0.11.0 (2019-07-11)
-------------------

- 移除对aiohttp的依赖，改由tornado实现HTTP请求，新增pycurl依赖
- 添加基于Selenium和Chrome driver的渲染器
- 添加Docker镜像 ``jadbin/xpaw`` ，便于构建爬虫运行环境
- 暂时移除对cookies和cookie jar的支持
- 组件cluster更名为crawler，包含cluster命名的模块、对象、函数、配置等均作出了相应的替换
- 运行爬虫工程的 ``run_crawler`` 接口更名为 ``run_spider_project``
- 非2xx的HttpResponse将视为请求失败并抛出 ``HttpError`` 异常进入错误处理流程
- RetryMiddleware不再raise IgnoreRequest，即因达到重试次数上限而导致请求失败时不再封装为IgnoreRequest，将保留原有的HttpResponse或异常
- HttpRequest ``proxy`` , ``timeout`` , ``verify_ssl`` , ``allow_redirects`` , ``auth`` ,  ``proxy_auth`` 由在 ``meta`` 中配置改为直接作为HttpRequest的属性
- Selector之前在遇到异常时会返回空数组，现在改为直接抛出异常
- 修改ProxyMiddleware的配置格式
- 移除ImitatingProxyMiddleware
- 修改SpeedLimitMiddleware的配置格式
- 移除 config.py 中的 ``downloader_timeout`` , ``verify_ssl`` , ``allow_redirects`` 配置项
- 移除 ``xpaw.FormData`` , ``xpaw.URL``
- 移除 ``xpaw.MultiDict`` , ``xpaw.CIMultiDict`` , 改由 ``xpaw.HttpHeaders`` 替代承载headers的功能
- 移除请求超时错误TimeoutError，统一由ClientError表示downloader抛出的异常
- ``default_headers`` 默认为 ``None`` , 浏览器默认的HTTP header改由UserAgentMiddleware根据设定的浏览器类型进行设置
- ``xpaw.downloadermws`` 模块更名为 ``xpaw.downloader_middlewares`` ， ``xpaw.spidermws`` 模块更名为 ``xpaw.spider_middlewares``
- ``@every`` 装饰器移至 ``xpaw.decorator`` 模块
- 移除对 ``dump_dir`` 的支持


0.10.4 (2018-11-06)
-------------------

- 在生成初始请求过程中，捕获单个请求抛出的异常并记录日志


0.10.3 (2018-09-01)
-------------------

- ProxyMiddleware不会覆盖用户在HttpRequest ``meta`` 中设置的 ``proxy``
- CookiesMiddleware不会覆盖用户在HttpRequest ``meta`` 中设置的 ``cookie_jar``
- NetworkError更名为ClientError，同时请求超时改由TimeoutError表示


0.10.2 (2018-08-28)
-------------------

- Field添加 ``type`` 参数，表示该字段的类型，在获取该字段的值时会进行类型转换
- 添加 ``allow_redirects`` 配置项，控制是否允许重定向，默认为 ``True``
- HttpRequest ``meta`` 添加 ``verify_ssl`` 和 ``allow_redirects`` 字段，用于精确控制单次请求的相关行为
- 添加 ``StopCluster`` 异常，用于在spider在回调函数中停止cluster
- 添加 ``request_ignored`` 事件
- ``user_agent`` 默认值设置为 ``:desktop``
- 运行spider之后不会再移除主程序已经设置的signal handler


0.10.1 (2018-07-18)
-------------------

- 新增 ``make_requests`` 函数，用于发起请求并获取对应的结果，详见 :ref:`make_requests`
- ``log_level`` 支持小写字母配置，如 ``debug`` 。


0.10.0 (2018-07-15)
-------------------

- ``xpaw crawl`` 支持直接运行spider，支持指定配置文件，添加了更多的功能选项
- 添加 ``daemon`` 配置项，支持以daemon模式运行爬虫
- 添加 ``pid_file`` 配置项，支持将爬虫所在进程的PID写入文件
- 添加 ``dump_dir`` 配置项，支持爬虫的暂停与恢复
- 运行spider结束时移除配置的log handler，避免先后多次运行spider时打印多余的日志
- 移除爬虫工程的入口文件setup.cfg，直接通过工程根目录下的config.py完成配置
- 重构ProxyMiddleware配置项
- 通过 ``speed_limit_enabled`` 控制限速中间件SpeedLimitMiddleware的开启/关闭，默认为关闭状态
- 配置项 ``verify_ssl`` 的默认值更改为 ``False``
- 配置项 ``queue_cls`` 更名为 ``queue``
- 配置项 ``dupe_filter_cls`` 更名为 ``dupe_filter``
- cluster的 ``stats_center`` 更名为 ``stats_collector`` ，配置项 ``stats_center_cls`` 更名为 ``stats_collector``
- 调整了中间件加载顺序权值
- HttpRequest对 ``auth`` , ``cookie_jar`` , ``proxy`` , ``proxy_auth`` 的配置移至 ``meta`` 属性中
- SetDupeFilter更名为HashDupeFilter
- 修改aiohttp的版本限制为>=3.3.2


0.9.1 (2018-04-16)
------------------

- 修复了setup.py中读取README的编码设置问题
- 不再只依赖于通过定时轮询判定job是否结束，单次下载完成后即判定job是否结束
- 修改依赖库的版本限制


0.9.0 (2017-11-13)
------------------

- 中间件的加载细分为内置中间件和用户自定义中间件两部分，内置中间件自动加载，用户中间件的加载由配置项确定
- 中间件加载的顺序由配置的权值确定，权值越大越贴近downloader/spider
- 添加 ``NotEnabled`` 异常，在中间件/拓展的构造函数中控制抛出该异常来实现开启或禁用该中间件/拓展。
- 添加UserAgentMiddleware，支持选择PC端或移动端的User-Agent，支持随机User-Agent
- 支持配置日志写入指定文件
- 修复了HttpRequest的fingerprint计算时没有考虑端口号的bug
- 移除ResponseNotMatchMiddleware
- 移除ProxyAgentMiddle，原有功能并入ProxyMiddleware
- 修改了RetryMiddleware,ProxyMiddleware,DepthMiddleware的参数配置方式
- ForwardedForMiddleware更名为ImitatingProxyMiddleware，用于设置HTTP请求头的 ``X-Forwarded-For`` 和 ``Via`` 字段
- 系统配置 ``downloader_verify_ssl`` 更名为 ``verify_ssl`` ， ``downloader_cookie_jar_enabled`` 更名为 ``cookie_jar_enabled``
- 更新了downloader和spider相关的错误处理流程
- 更新了判定job结束的逻辑


0.8.0 (2017-11-5)
-----------------

- spider的 ``start_requests`` 和 ``parse`` 函数支持async类型和python 3.6中的async generator类型
- spider中间件的handle_*函数支持async类型
- 添加事件驱动相关的eventbus和events模块，支持事件的订阅/发送，可通过 ``cluster.event_bus`` 获取event bus组件
- 捕获SIGINT和SIGTERM信号并做出相应处理
- 添加extension模块，支持用户自定义拓展
- 添加statscenter模块，用于收集,管理系统产生的各项统计量，可通过 ``cluster.stats_center`` 获取stats center组件；
  系统配置添加 ``stats_center_cls`` 项，用于替换默认的stats center的实现
- SetDupeFilter添加 ``clear`` 函数
- 系统配置添加 ``downloader_verify_ssl`` 项，用于开启或关闭SSL证书认证
- HttpRequest的 ``body`` 参数支持 ``bytes`` , ``str`` , ``FormData`` , ``dict`` 等形式
- HttpRequest添加 ``params`` , ``auth`` , ``proxy_auth`` , ``priority`` 等属性
- 添加深度优先队列LifoQueue，以及优先级队列PriorityQueue，默认 ``queue_cls`` 更改为 ``xpaw.queue.PriorityQueue``
- 支持设定HTTP请求的优先级并按优先级进行爬取
- 添加item,pipeline模块，支持spider在处理response时返回BaseItem的实例或dict，并交由用户自定义的item pipelines进行处理
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

- 通过 ``@every`` 实现定时任务功能
- HttpRequest添加 ``dont_filter`` 字段，为 ``True`` 时表示该请求不会被过滤
- ``xpaw.run`` 模块中添加 ``run_spider`` 函数，便于在python代码中直接运行Spider类
- ``xpaw.utils.run`` 模块中 ``run_crawler`` 函数移动至 ``xpaw.run`` 模块
- 原utils, commands, downloadersmws, spidermws各合并为一个模块


0.7.0 (2017-10-24)
------------------

- 使用继承Dupefilter的去重过滤器来实现去重功能，系统配置添加 ``dupefilter_cls`` 项，用于替换默认的去重过滤器
- ``xpaw.utils.run`` 模块中添加 ``run_crawler`` 函数，便于在python代码中控制开启爬虫
- 使用config.py替代config.yaml作为配置文件，移除对pyyaml的依赖
- ForwardedForMiddleware移动到 ``xpaw.downloadermws.headers`` 模块下
- 修改aiohttp的版本限制为>=2.2.0
- 更新了downloader和spider相关的错误处理流程
- 不再采用中间件的形式实现请求的去重功能，并移除相关的中间件
- ProxyAgentMiddleware的 ``proxy_agent`` 配置下面 ``addr`` 字段更名为 ``agent_addr``


0.6.5 (2017-05-09)
------------------

- HttpRequest添加 ``errback`` 字段，表示无法正常获取到HttpResponse时触发的函数
- ResponseMatchMiddleware的配置修改为列表
- middleware的顺序修改为依次向downloader/spider靠近，层层包裹
- 移除任务配置中随机生成的 ``task_id``


0.6.4 (2017-05-05)
------------------

- HttpResponse中的 ``url`` 字段源于aiohttp返回的ClientResponse中的 ``url`` 字段，实际应为 ``yarl.URL`` 对象
- LocalCluster启动时不再新建一个线程
- 优化日志工具中设置日志的接口


0.6.2 (2017-03-30)
------------------

- HttpResponse添加 ``encoding`` 和 ``text`` 字段，分别用于获取网页的编码及字符串形式的内容
- 添加ResponseMatchMiddleware，用于初步判断得到的页面是否符合要求
- 添加CookieJarMiddleware，用于维护请求过程中产生的cookie，同时HttpRequest ``meta`` 中添加系统项 ``cookie_jar`` 作为发起请求时使用的cookie jar
- HttpRequest ``meta`` 添加 ``timeout`` 字段，用于精确控制某个请求的超时时间
- 系统配置添加 ``queue_cls`` 项，用于替换默认的请求队列


0.6.1 (2017-03-23)
------------------

- 中间件添加 ``open`` 和 ``close`` 两个钩子函数，分别对应开启和关闭爬虫的事件
- RetryMiddleware中可以自定义需要重试的HTTP状态码
- 添加SpeedLimitMiddleware，用于爬虫限速
- 添加ProxyMiddleware，用于为请求添加指定代理
- 移除MongoDedupeMiddleware及对pymongo的依赖
- 修改ProxyAgentMiddleware,RetryMiddleware在配置文件中的参数格式
- DepthMiddleware更名为MaxDepthMiddleware


0.6.0 (2017-03-16)
------------------

- First release
