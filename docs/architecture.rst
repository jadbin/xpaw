.. _architecture:

Architecture Overview
=====================

这里我们会对xpaw的结构进行简要的介绍。

首先我们会给出爬虫运行过程中的数据流图，接着我们会对数据流中呈现的各个组件进行简要的介绍。

Data Flow
---------

.. image:: _static/data_flow.png

数据流以cluster为核心，并由cluster进行控制和驱动:

1. cluster从spider中获取初始的requests。
2. cluster将得到的初始的requests放入到queue中。
3. cluster不停地从queue中获取待处理的request。
4. cluster将request交由downloader发起实际的请求。
5. downloader将请求得到response返回给cluster。
6. cluster将得到的response交由spider中指定的处理函数进行处理。
7. spider处理response并返回提取的items和新的requests。
8. cluster将得到的items交由pipelines做进一步处理，将得到的requests继续放入到queue中。

爬虫会持续运行直到所有产生的requests都被处理完且不再产生新的requests为止。

Components
----------

Cluster
^^^^^^^

Queue
^^^^^

Downloader
^^^^^^^^^^

Spider
^^^^^^

Pipeline
^^^^^^^^
