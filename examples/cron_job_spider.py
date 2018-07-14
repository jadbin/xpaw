# coding=utf-8

from xpaw import Spider, HttpRequest, Selector, every, run_spider


class CronJobSpider(Spider):
    @every(seconds=10)
    def start_requests(self):
        yield HttpRequest("http://news.qq.com/", callback=self.parse, dont_filter=True)

    def parse(self, response):
        selector = Selector(response.text)
        major_news = selector.css("div.major a.linkto").text
        self.log("Major news:")
        for i in range(len(major_news)):
            self.log("%s: %s", i + 1, major_news[i])


if __name__ == '__main__':
    run_spider(CronJobSpider, log_level='DEBUG')
