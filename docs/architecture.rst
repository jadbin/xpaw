.. _architecture:

Architecture Overview
=====================

这里我们会对xpaw的结构进行简要的介绍。

首先我们会给出爬虫运行过程中的数据流图，接着我们会对数据流中呈现的各个组件进行简要的介绍。

Data Flow
---------

数据流以cluster为核心，并由cluster进行控制和驱动：

.. image:: _static/data_flow.png

1. cluster从spider中获取初始请求requests。
2. cluster将得到requests放入到queue中。
3. cluster不停地从queue中获取待处理的request。
4. cluster将request交由downloader处理。
5. downloader完成下载后生成response返回给cluster。
6. cluster将得到的response交由spider处理。
7. spider处理response并提取数据items和新的请求requests。
8. cluster将得到的items交由pipelines处理，将得到的requests放入到queue中。

爬虫会持续运行直到所有生成的requests都被处理完且不再生成新的requests为止。

Components
----------

Cluster
^^^^^^^

实现对各个组件的控制和驱动。

Queue
^^^^^

存储HTTP请求的队列。

Downloader
^^^^^^^^^^

基于协程实现异步下载功能。

Spider
^^^^^^

用户在Spider中实现采集任务的核心逻辑，包括网页解析、数据抽取、链接抽取等。

Pipeline
^^^^^^^^

处理采集得到的结构化数据。
