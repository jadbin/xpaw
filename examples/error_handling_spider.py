# coding=utf-8

from xpaw import Spider, HttpRequest, run_spider
from xpaw.errors import HttpError, ClientError, RequestTimeout


class ErrorHandlingSpider(Spider):
    start_urls = [
        "http://www.python.org/",  # 200 OK
        "http://www.httpbin.org/status/404",  # 404 Not Found
        "http://www.httpbin.org/status/500",  # 500 Service Not Available
        "http://www.example.com:8080/",  # RequestTimeout
        "http://foo.example.com/",  # ClientError
    ]

    def start_requests(self):
        for url in self.start_urls:
            yield HttpRequest(url, errback=self.handle_error)

    def parse(self, response):
        self.logger.info('Successful response: %s', response)

    def handle_error(self, request, error):
        if isinstance(error, HttpError):
            response = error.response
            self.logger.error('HttpError on %s: HTTP status=%s', request.url, response.status)
        elif isinstance(error, RequestTimeout):
            self.logger.error('RequestTimeout on %s', request.url)
        elif isinstance(error, ClientError):
            self.logger.error('ClientError on %s: %s', request.url, error)


if __name__ == '__main__':
    run_spider(ErrorHandlingSpider, retry_enabled=False)
