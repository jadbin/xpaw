# coding=utf-8

from xpaw.eventbus import EventBus
from xpaw.config import Config, DEFAULT_CONFIG


class Crawler:
    def __init__(self, **kwargs):
        self.event_bus = EventBus()
        self.config = Config(DEFAULT_CONFIG, **kwargs)
