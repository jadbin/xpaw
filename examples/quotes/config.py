# coding=utf-8

project_name = 'quotes'
project_description = ''

# Configure spider
spider = 'quotes.spider.QuotesSpider'

# Configure item pipelines
item_pipelines = [
    'quotes.pipelines.QuotesPipeline'
]
