# coding=utf-8

from urllib.parse import urljoin

from xpaw import Spider, HttpRequest, Selector

from .items import QuotesItem


class QuotesSpider(Spider):
    def start_requests(self):
        yield HttpRequest('http://quotes.toscrape.com/', callback=self.parse)

    def parse(self, response):
        selector = Selector(response.text)
        for quote in selector.css('div.quote'):
            text = quote.css('span.text')[0].text
            author = quote.css('small.author')[0].text
            author_url = quote.css('small+a')[0].attr('href')
            author_url = urljoin(str(response.url), author_url)
            tags = quote.css('div.tags a').text
            yield QuotesItem(text=text, tags=tags,
                             author=author, author_url=author_url)
        next_page = selector.css('li.next a')
        if len(next_page) > 0:
            next_page_url = urljoin(str(response.url), next_page[0].attr('href'))
            yield HttpRequest(next_page_url, callback=self.parse)
