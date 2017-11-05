# coding=utf-8

from xpaw import Spider, HttpRequest, Selector
from xpaw.handler import every
from xpaw.run import run_spider


class CronJobSpider(Spider):
    @every(seconds=10)
    def start_requests(self):
        yield HttpRequest("http://quotes.toscrape.com/", callback=self.parse, dont_filter=True)

    def parse(self, response):
        selector = Selector(response.text)
        tags = selector.css("div.tags-box a").text
        self.log("Top ten tags: %s", tags)


if __name__ == '__main__':
    run_spider(CronJobSpider, log_level="DEBUG")
