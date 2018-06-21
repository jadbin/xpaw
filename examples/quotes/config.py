# coding=utf-8

# Configuration file, created by xpaw/0.10.0 on Jun 20 2018 11:24:39

project_name = 'quotes'
project_description = ''

# Configure spider
spider = 'quotes.spider.QuotesSpider'

# Configure item pipelines
item_pipelines = [
    'quotes.pipelines.QuotesPipeline'
]

# Configure downloader clients, i.e. the maximum concurrent requests (default: 100)
# downloader_clients = 1

# Enable cookie jar (disabled by default)
# cookie_jar_enabled = True

# Disable SSL verification (enabled by default)
# verify_ssl = False

# Enable and configure speed limit (disabled by default)
# speed_limit_enabled = True
# speed_limit_rate = 1
# speed_limit_burst = 1

# Override the default request headers:
# default_headers = {
#     'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
#     'Accept-Encoding': 'gzip, deflate',
#     'Accept-Language': 'zh-CN,zh;q=0.8',
#     'Cache-Control': 'max-age=0',
#     'Connection': 'keep-alive',
#     'Upgrade-Insecure-Requests': '1'
# }

# Configure user agent
user_agent = ':desktop'

# Enable imitating proxy, i.e. adding 'X-Forwarded-For' and 'Via' headers (disabled by default)
imitating_proxy_enabled = True

# Configure proxy
# proxy = None
# proxy_provider = None

# Enable or disable downloader middlewares
# downloader_middlewares = {}

# Enable or disable spider middlewares
# spider_middlewares = {}

# Enable or disable extensions
# extensions = {}