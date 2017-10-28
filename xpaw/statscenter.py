# coding=utf-8


class StatsCenter:
    def __init__(self):
        self.stats = {}

    def get(self, key, default=None):
        return self.stats.get(key, default)

    def set(self, key, value):
        self.stats[key] = value

    def set_default(self, key, default=None):
        self.stats.setdefault(key, default)

    def set_min(self, key, value):
        self.stats[key] = min(self.stats.setdefault(key, value), value)

    def set_max(self, key, value):
        self.stats[key] = max(self.stats.setdefault(key, value), value)

    def inc(self, key, value=1, start=0):
        self.stats[key] = self.stats.setdefault(key, start) + value


class EmptyStatusCenter(StatsCenter):
    def get(self, key, default=None):
        return default

    def set(self, key, value):
        pass

    def set_default(self, key, default=None):
        pass

    def set_min(self, key, value):
        pass

    def set_max(self, key, value):
        pass

    def inc(self, key, value=1, start=0):
        pass
