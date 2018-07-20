.. _selector:

Selector
========

Selector是基于 `lxml`_ 和 `cssselect`_ 封装的网页内容选择器，用于定位数据所在的网页节点，并对数据进行提取。
Selector相关API可以参考 :ref:`selector_api` 。

.. _lxml: https://pypi.python.org/pypi/lxml
.. _cssselect: https://pypi.python.org/pypi/cssselect

Selector Usage
--------------

我们通过一个实例来说明Selector的使用方法，相关代码位于 `examples/selector_usage.py <https://github.com/jadbin/xpaw/tree/master/examples/selector_usage.py>`_ 。

下面给出的是 `quotes.toscrape.com <http://quotes.toscrape.com/>`_ 的简化版网页，我们需要提取网页中展示的quote。

.. code-block:: html

    <html>
    <head>
        <title>Quotes to Scrape</title>
        <link rel="stylesheet" href="/static/main.css">
    </head>
    <body>
        <div class="quote" itemscope itemtype="http://schema.org/CreativeWork">
            <span class="text" itemprop="text">“I have not failed. I&#39;ve just found 10,000 ways that won&#39;t work.”</span>
            <span>by <small class="author" itemprop="author">Thomas A. Edison</small>
            <a href="/author/Thomas-A-Edison">(about)</a>
            </span>
            <div class="tags">
                Tags:
                <a class="tag" href="/tag/edison/page/1/">edison</a>
                <a class="tag" href="/tag/failure/page/1/">failure</a>
                <a class="tag" href="/tag/inspirational/page/1/">inspirational</a>
                <a class="tag" href="/tag/paraphrased/page/1/">paraphrased</a>
            </div>
        </div>
        <div class="quote" itemscope itemtype="http://schema.org/CreativeWork">
            <span class="text" itemprop="text">“It is our choices, Harry, that show what we truly are, far more than our abilities.”</span>
            <span>by <small class="author" itemprop="author">J.K. Rowling</small>
            <a href="/author/J-K-Rowling">(about)</a>
            </span>
            <div class="tags">
                Tags:
                <a class="tag" href="/tag/abilities/page/1/">abilities</a>
                <a class="tag" href="/tag/choices/page/1/">choices</a>
            </div>
        </div>
    </body>
    </html>

Constructing Selectors
^^^^^^^^^^^^^^^^^^^^^^

假设上面的网页内容存储在变量 ``text`` 中，我们可以通过如下的方式构造Selector：

.. code-block:: python

    from xpaw import Selector

    selector = Selector(text)

Locating Elements
^^^^^^^^^^^^^^^^^

我们可以使用CSS Selector语法或XPath语法定位数据所在的节点。

有关CSS Selector语法的详细信息，可以参考 `CSS Selector Reference <http://w3schools.bootcss.com/cssref/css_selectors.html>`_ 。
有关XPath语法的详细信息可以参考 `XPath Syntax <http://w3schools.bootcss.com/xsl/xpath_syntax.html>`_ 。

首先我们需要观察数据所在节点的在标签层次上的特征，然后再将这种特征通过CSS Selector语法或XPath语法进行描述。

例如，我们可以观察到每个quote都在一个 ``class=quote`` 的 ``<div>`` 标签中，每个quote的内容都在一个 ``class=text`` 的 ``span`` 标签中。
接下来，我们可以用CSS Selector语法对这些特征进行描述，并借助Selector来提取quote的内容：

.. code-block:: python

    print('# CSS Selector, content of quotes:')
    for quote in selector.css('div.quote'):
        print(quote.css('span.text')[0].text)

.. code-block:: text

    # CSS Selector, content of quotes:
    “I have not failed. I've just found 10,000 ways that won't work.”
    “It is our choices, Harry, that show what we truly are, far more than our abilities.”

也可以用XPath语法对这些特征进行描述，并借助Selector来提取quote的内容：

.. code-block:: python

    print('# XPath, content of quotes:')
    for quote in selector.xpath('//div[@class="quote"]'):
        print(quote.xpath('.//span[@class="text"]')[0].text)

.. code-block:: text

    # XPath, content of quotes:
    “I have not failed. I've just found 10,000 ways that won't work.”
    “It is our choices, Harry, that show what we truly are, far more than our abilities.”

根据观察的特征不同，我们可能会写出不同的表达式。
例如，我们也可以认为每个quote的内容在 ``itemprop="text"`` 的 ``span`` 标签中：

.. code-block:: python

    for quote in selector.css('div.quote'):
        print(quote.css('span[itemprop="text"]')[0].text)

``css`` 和 ``xpath`` 是可以级联使用的，例如：

.. code-block:: python

    for t in selector.css('div.quote').css('span.text'):
        print(t.text)

``css`` 和 ``xpath`` 也可以混合使用，例如：

.. code-block:: python

    for t in selector.xpath('//div[@class="quote"]').css('span.text'):
        print(t.text)

Extracting Data
^^^^^^^^^^^^^^^

除了前面展示的可以通过 ``text`` 属性获取节点中不包含标签的文本，我们还可以通过 ``string`` 属性获取完整的带标签的内容：

.. code-block:: python

    print('# CSS Selector, content of quotes, with HTML tags:')
    for quote in selector.css('div.quote'):
        print(quote.css('span.text')[0].string)

.. code-block:: text

    # CSS Selector, content of quotes, with HTML tags:
    <span class="text" itemprop="text">“I have not failed. I've just found 10,000 ways that won't work.”</span>
    <span class="text" itemprop="text">“It is our choices, Harry, that show what we truly are, far more than our abilities.”</span>

对于选择出的节点列表，同样可以采用这样的方式获取数据，得到的即为数据的列表。
例如我们获取每个quote下面所有的tag：

.. code-block:: python

    print('# CSS Selector, quote tags')
    for quote in selector.css('div.quote'):
        print(quote.css('a.tag').text)

.. code-block:: text

    # CSS Selector, quote tags
    ['edison', 'failure', 'inspirational', 'paraphrased']
    ['abilities', 'choices']

如果需要获取节点属性值，则可以使用 ``attr()`` 。
例如我们获取quote作者的链接：

.. code-block:: python

    print('# CSS Selector, author urls')
    for quote in selector.css('div.quote'):
        print(quote.css('small+a')[0].attr('href'))

.. code-block:: text

    # CSS Selector, author urls
    /author/Thomas-A-Edison
    /author/J-K-Rowling

.. _selector_api:

Selector API
------------

.. class:: xpaw.selector.Selector(text=None, root=None, text_type=None)

    节点和数据的选择器。

    :param str text: HTML或XML文本
    :param root: 根节点，``text`` 和 ``root`` 只需指定其中一个，当指定 ``text`` 时，会自动创建 ``root`` 。
    :param str text_type: ``html`` 或 ``xml``，默认为 ``html`` 。

    .. attribute:: root

        根节点

    .. method:: css(css, **kwargs)

        使用CSS Selector语法选择节点。

        :param str css: CSS Selector语法描述
        :return: 选择的节点对应的 :class:`~xpaw.selector.SelectorList`

    .. method:: xpath(xpath, **kwargs)

        使用XPath语法选择节点。

        :param str xpath: XPath语法描述
        :return: 选择的节点对应的 :class:`~xpaw.selector.SelectorList`

    .. attribute:: string

        获取节点包括标签在内的全部内容。

    .. attribute:: text

        获取节点去掉标签后的文本内容。

    .. method:: attr(name)

        获取节点的属性。

        :param str name: 属性名称


.. class:: xpaw.selector.SelectorList

    :class:`~xpaw.selector.SelectorList` 是由 :class:`~xpaw.selector.Selector` 组成的 ``list`` 。

    .. method:: css(css, **kwargs)

        对其中的每一个 :class:`~xpaw.selector.Selector` 使用CSS Selector语法选择节点。

        :param str css: CSS Selector语法描述
        :return: 选择的节点对应的 :class:`~xpaw.selector.SelectorList`

    .. method:: xpath(xpath, **kwargs)

        对其中的每一个 :class:`~xpaw.selector.Selector` 使用XPath语法选择节点。

        :param str xpath: XPath语法描述
        :return: 选择的节点对应的 :class:`~xpaw.selector.SelectorList`

    .. attribute:: string

        获取各个节点包括标签在内的全部内容，返回 ``list`` 。

    .. attribute:: text

        获取各个节点去掉标签后的文本内容，返回 ``list`` 。

    .. method:: attr(name)

        获取各个节点的属性，返回 ``list`` 。

        :param str name: 属性名称
