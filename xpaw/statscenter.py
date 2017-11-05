# coding=utf-8


class StatsCenter:
    def __init__(self):
        self._stats = {}

    def get(self, key, default=None):
        return self._stats.get(key, default)

    def set(self, key, value):
        self._stats[key] = value

    def set_default(self, key, default=None):
        self._stats.setdefault(key, default)

    def set_min(self, key, value):
        self._stats[key] = min(self._stats.setdefault(key, value), value)

    def set_max(self, key, value):
        self._stats[key] = max(self._stats.setdefault(key, value), value)

    def inc(self, key, value=1, start=0):
        self._stats[key] = self._stats.setdefault(key, start) + value

    def clear(self):
        self._stats.clear()

    def remove(self, key):
        if key in self._stats:
            del self._stats[key]

    @property
    def stats(self):
        return self._stats

    def set_stats(self, stats):
        self._stats = stats


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

    def set_stats(self, stats):
        pass
