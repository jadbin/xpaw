# coding=utf-8

from xpaw import Item, Field


class QuotesItem(Item):
    text = Field()
    author = Field()
    author_url = Field()
    tags = Field()
