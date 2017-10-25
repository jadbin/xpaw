# coding=utf-8

from xpaw import Spider, HttpRequest, Selector
from xpaw.run import run_spider


class TutorialSpider(Spider):
    def __init__(self, config):
        super().__init__(config)

    def start_requests(self):
        yield HttpRequest("http://news.qq.com", callback=self.parse)

    def parse(self, response):
        selector = Selector(response.text)
        major_news = selector.xpath("//div[@class='item major']//a[@class='linkto']").text
        self.log("Major news:")
        for i in range(len(major_news)):
            self.log("{}: {}".format(i + 1, major_news[i]))


if __name__ == '__main__':
    run_spider(TutorialSpider, log_level="DEBUG")
