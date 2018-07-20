# coding=utf-8

from urllib.parse import urljoin
import json

from xpaw import Spider, HttpRequest, Selector, run_spider


class QuotesSpider(Spider):
    quotes = []

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
            self.quotes.append(dict(text=text, tags=tags,
                                    author=author, author_url=author_url))
        next_page = selector.css('li.next a')
        if len(next_page) > 0:
            next_page_url = urljoin(str(response.url), next_page[0].attr('href'))
            yield HttpRequest(next_page_url, callback=self.parse)

    def close(self):
        with open('quotes.json', 'w') as f:
            json.dump(self.quotes, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    run_spider(QuotesSpider, log_level='DEBUG')
