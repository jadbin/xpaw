# coding=utf-8

from urllib.parse import urljoin

from xpaw import Spider, HttpRequest, Selector

from .items import QuotesItem


class QuotesSpider(Spider):
    def start_requests(self):
        yield HttpRequest('http://quotes.toscrape.com/', callback=self.parse)

    def parse(self, response):
        selector = Selector(response.text)
        for quote in selector.xpath('//div[@class="quote"]'):
            text = quote.xpath('.//span[@itemprop="text"]')[0].text
            author = quote.xpath('.//small[@itemprop="author"]')[0].text
            author_url = quote.xpath('.//span/a/@href')[0].text
            author_url = urljoin(str(response.url), author_url)
            tags = quote.xpath('.//div[@class="tags"]/a').text
            yield QuotesItem(text=text, tags=tags,
                             author=author, author_url=author_url)
        next_page = selector.xpath('//li[@class="next"]/a/@href')
        if len(next_page) > 0:
            next_page_url = urljoin(str(response.url), next_page[0].text)
            yield HttpRequest(next_page_url, callback=self.parse)
