# coding=utf-8

from xpaw import Spider, HttpRequest, Selector, run_spider


class AsyncGeneratorSpider(Spider):
    """
    Need Python 3.6+
    """

    async def start_requests(self):
        yield HttpRequest("http://quotes.toscrape.com/", callback=self.parse)

    async def parse(self, response):
        selector = Selector(response.text)
        tags = selector.xpath("//div[contains(@class, 'tags-box')]//a").text
        self.log("Top ten tags: %s", tags)
        yield HttpRequest("http://quotes.toscrape.com/", callback=self.parse)


if __name__ == '__main__':
    run_spider(AsyncGeneratorSpider)
