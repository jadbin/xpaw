.. xpaw documentation master file, created by
   sphinx-quickstart on Thu Mar 16 11:08:48 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


============================
xpaw |version| documentation
============================

Key Features
============

- Provides a web scraping framework used to crawl web pages.
- Provides data extraction tools used to extract structured data from web pages.

Installation
============

安装xpaw需要Python 3.5及更高版本的环境支持。

可以直接使用如下命令通过PyPI安装:

.. code-block:: bash

    $ pip install xpaw

也可使用如下命令通过源码安装:

.. code-block:: bash

    $ python setup.py install

如果安装过程中遇到lxml安装失败的情况，可参考 `lxml installation`_ 。

.. _lxml installation: http://lxml.de/installation.html

Requirements
============

- `aiohttp`_
- `lxml`_

.. _aiohttp: https://pypi.python.org/pypi/aiohttp
.. _lxml: https://pypi.python.org/pypi/lxml

Contents
========

.. toctree::
   :maxdepth: 2

   quickstart
   usage

All the Rest
============

.. toctree::
   :maxdepth: 1

   changelog
