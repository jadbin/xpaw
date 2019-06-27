# coding=utf-8

from xpaw import Spider, HttpRequest, Selector, run_spider


class RenderingSpider(Spider):
    def start_requests(self):
        yield HttpRequest('http://quotes.toscrape.com/js/', callback=self.parse, render=True)

    def parse(self, response):
        selector = Selector(response.text)
        for quote in selector.css('div.quote'):
            text = quote.css('span.text')[0].text
            author = quote.css('small.author')[0].text
            self.log(author + ": " + text)


if __name__ == '__main__':
    run_spider(RenderingSpider)
