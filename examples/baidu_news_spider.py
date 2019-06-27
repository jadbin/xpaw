# coding=utf-8

from xpaw import Spider, HttpRequest, Selector, run_spider


class BaiduNewsSpider(Spider):
    def start_requests(self):
        yield HttpRequest("http://news.baidu.com/", callback=self.parse)

    def parse(self, response):
        selector = Selector(response.text)
        hot = selector.css("div.hotnews a").text
        self.log("Hot News:")
        for i in range(len(hot)):
            self.log("%s: %s", i + 1, hot[i])


if __name__ == '__main__':
    run_spider(BaiduNewsSpider)
