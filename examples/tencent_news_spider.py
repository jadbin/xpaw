# coding=utf-8

from xpaw import Spider, HttpRequest, Selector, run_spider


class TencentNewsSpider(Spider):
    def start_requests(self):
        yield HttpRequest("http://news.qq.com/", callback=self.parse)

    def parse(self, response):
        selector = Selector(response.text)
        major_news = selector.css("div.major a.linkto").text
        self.log("Major news:")
        for i in range(len(major_news)):
            self.log("%s: %s", i + 1, major_news[i])


if __name__ == '__main__':
    run_spider(TencentNewsSpider)
