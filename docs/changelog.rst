.. _changelog:

Change log
==========

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
