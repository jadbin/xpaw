# coding=utf-8

text = '''
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
'''

if __name__ == '__main__':
    from xpaw import Selector

    selector = Selector(text)

    print('# CSS Selector, content of quotes:')
    for quote in selector.css('div.quote'):
        print(quote.css('span.text')[0].text)

    print('# XPath, content of quotes:')
    for quote in selector.xpath('//div[@class="quote"]'):
        print(quote.xpath('.//span[@class="text"]')[0].text)

    print('# CSS Selector, content of quotes, with HTML tags:')
    for quote in selector.css('div.quote'):
        print(quote.css('span.text')[0].string)

    print('# CSS Selector, quote tags')
    for quote in selector.css('div.quote'):
        print(quote.css('a.tag').text)

    print('# CSS Selector, author urls')
    for quote in selector.css('div.quote'):
        print(quote.css('small+a')[0].attr('href'))
