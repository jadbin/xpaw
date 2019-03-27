# coding=utf-8

from xpaw import Spider, HttpRequest, Selector, run_spider


class BaikeHotSearchSpider(Spider):
    def start_requests(self):
        yield HttpRequest("http://baike.baidu.com/", callback=self.parse)

    def parse(self, response):
        selector = Selector(response.text)
        major_news = selector.css("div.content_tit span").text
        self.log("Hot Search:")
        for i in range(len(major_news)):
            self.log("%s: %s", i + 1, major_news[i])


if __name__ == '__main__':
    run_spider(BaikeHotSearchSpider)
