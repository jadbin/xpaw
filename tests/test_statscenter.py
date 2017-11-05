# coding=utf-8

from xpaw.statscenter import StatsCenter, EmptyStatusCenter


class TestStatsCenter:
    def test_get_none_key(self):
        stats = StatsCenter()
        assert stats.get('key') is None
        assert stats.get('key', 'default') is 'default'
        stats.set('key', 'value')
        assert stats.get('key', 'default') == 'value'

    def test_set_value(self):
        stats = StatsCenter()
        stats.set('key1', 0)
        assert stats.get('key1') == 0
        stats.set_max('key1', 2)
        assert stats.get('key1') == 2
        stats.set_max('key1', 1)
        assert stats.get('key1') == 2
        stats.set_max('key2', 3)
        assert stats.get('key2') == 3
        stats.set('key3', 5)
        assert stats.get('key3') == 5
        stats.set_min('key3', 4)
        assert stats.get('key3') == 4
        stats.set_min('key3', 6)
        assert stats.get('key3') == 4
        stats.set_min('key4', 1)
        assert stats.get('key4') == 1
        stats.set_default('key5', 6)
        assert stats.get('key5') == 6
        stats.set_default('key5', 5)
        assert stats.get('key5') == 6

    def test_inc_value(self):
        stats = StatsCenter()
        stats.set('key1', 1)
        stats.inc('key1')
        assert stats.get('key1') == 2
        stats.inc('key1', 2)
        assert stats.get('key1') == 4
        stats.inc('key1', 5, start=0)
        assert stats.get('key1') == 9
        stats.inc('key2')
        assert stats.get('key2') == 1
        stats.inc('key3', start=1)
        assert stats.get('key3') == 2
        stats.inc('key4', 2, start=3)
        assert stats.get('key4') == 5

    def test_clear_stats(self):
        stats = StatsCenter()
        stats.set('key1', 1)
        stats.set('key2', 2)
        assert stats.stats == {'key1': 1, 'key2': 2}
        stats.clear()
        assert stats.stats == {}

    def test_set_stats(self):
        stats = StatsCenter()
        stats.set_stats({'key1': 1, 'key2': 2})
        assert stats.stats == {'key1': 1, 'key2': 2}

    def test_remove_key(self):
        stats = StatsCenter()
        stats.set('key', 'value')
        assert stats.get('key') == 'value'
        stats.remove('key')
        assert stats.get('key') is None
        assert stats.get('key', 'default') == 'default'


class TestEmptyStatsCenter:
    def test_set_value(self):
        stats = EmptyStatusCenter()
        assert stats.get('key') is None
        stats.set('key', 'value')
        assert stats.get('key') is None
        assert stats.get('key', 'default') == 'default'
        stats.set_min('key', 0)
        assert stats.get('key') is None
        stats.set_max('key', 0)
        assert stats.get('key') is None
        stats.set_default('key', 'value')
        assert stats.get('key') is None

    def test_inc_value(self):
        stats = EmptyStatusCenter()
        stats.inc('key')
        assert stats.get('key') is None

    def test_set_stats(self):
        stats = EmptyStatusCenter()
        stats.set_stats({'key1': 1, 'key2': 2})
        assert stats.stats == {}
