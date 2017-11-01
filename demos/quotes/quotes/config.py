# coding=utf-8

# version=0.8.0
# Configuration file, created automatically on Nov 01 2017 21:09:01

# ===================================================================
# Project configuration
# ===================================================================

project_name = 'quotes'
project_description = ''

downloader_middlewares = [
    # 'xpaw.downloadermws.ProxyAgentMiddleware',
    'xpaw.downloadermws.DefaultHeadersMiddleware',
    'xpaw.downloadermws.ForwardedForMiddleware',
    'xpaw.downloadermws.RetryMiddleware'
]

spider_middlewares = []

spider = 'quotes.spider.QuotesSpider'

item_pipelines = [
    'quotes.pipelines.QuotesPipeline'
]

extensions = []

# ===================================================================
# System specific properties
# ===================================================================

proxy_agent = {
    'agent_addr': 'http://<address>:<port><path>'
}

default_headers = {
    'Connection': 'keep-alive',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36',
    'Accept-Encoding': 'gzip, deflate, sdch',
    'Accept-Language': 'zh-CN,zh;q=0.8'
}

# ===================================================================
# Project specific properties
# Add your own properties here
# ===================================================================
