# coding=utf-8

from xpaw import Spider, HttpRequest, Selector
from xpaw.run import run_spider


class RunningSingleSpider(Spider):
    def start_requests(self):
        yield HttpRequest("http://quotes.toscrape.com/", callback=self.parse)

    def parse(self, response):
        selector = Selector(response.text)
        tags = selector.css("div.tags-box a").text
        self.log("Top ten tags: %s", tags)


if __name__ == '__main__':
    run_spider(RunningSingleSpider, log_level="DEBUG")
