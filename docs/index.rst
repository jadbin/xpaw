=========================
Welcome to xpaw |version|
=========================

Key Features
============

- A web scraping framework used to crawl web pages
- Data extraction tools used to extract structured data from web pages

Installation
============

安装xpaw需要Python 3.5.3或更高版本的环境支持。

可以使用如下命令安装xpaw:

.. code-block:: bash

    $ pip install xpaw

如果安装过程中遇到lxml安装失败的情况，可参考 `lxml installation <http://lxml.de/installation.html>`_ 。

Requirements
============

- Python >= 3.5.3
- `tornado`_
- `lxml`_
- `cssselect`_
- `selenium`_

.. _tornado: https://pypi.python.org/pypi/tornado
.. _lxml: https://pypi.python.org/pypi/lxml
.. _cssselect: https://pypi.python.org/pypi/cssselect
.. _selenium: https://pypi.python.org/pypi/selenium

Table of Contents
=================

.. toctree::
    :caption: Getting Started
    :maxdepth: 2

    make_requests
    tutorial1
    tutorial2

.. toctree::
    :caption: Basic References
    :maxdepth: 2

    spider
    req_resp
    selector
    settings
    errors

.. toctree::
    :caption: Advanced Usage
    :maxdepth: 2

    architecture
    core_api
    problems

.. toctree::
    :caption: All the Rest
    :maxdepth: 1

    changelog
