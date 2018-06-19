# coding=utf-8

import json
from os.path import dirname, join

home_dir = dirname(dirname(__file__))


class QuotesPipeline:
    def __init__(self):
        self.data = []

    def handle_item(self, item):
        self.data.append(dict(item))

    def close(self):
        with open(join(home_dir, 'quotes.json'), 'w') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)
