# coding=utf-8

from xpaw.config import BaseConfig, Config, KNOWN_SETTINGS


class TestBaseConfig:
    def test_get(self):
        d = {'key': 'value'}
        config = BaseConfig(values=d)
        assert len(config) == 1
        for k in config:
            assert k == 'key' and config[k] == 'value'
        assert config.get('key') == 'value'
        assert config.get('no_such_key') is None
        assert config.get('no_such_key', 'default') == 'default'
        assert config.get('key', 'default') == 'value'
        assert config['key'] == 'value'
        assert config['no_such_key'] is None
        assert ('key' in config) is True
        assert ('no_such_key' in config) is False

    def test_get_bool(self):
        d = {'bool_true': 'true', 'bool_True': 'True', 'bool_false': 'false', 'bool_False': 'False',
             'bool_int1': '1', 'bool_int0': '0', 'bool_none': '...',
             'true': True, 'false': False}
        config = BaseConfig(values=d)
        assert config.getbool('true') is True
        assert config.getbool('false') is False
        assert config.getbool('bool_true') is True
        assert config.getbool('bool_True') is True
        assert config.getbool('bool_false') is False
        assert config.getbool('bool_False') is False
        assert config.getbool('bool_int1') is True
        assert config.getbool('bool_int0') is False
        assert config.getbool('bool_none') is None
        assert config.getbool('bool_no') is None
        assert config.getbool('bool_no', True) is True
        assert config.getbool('bool_no', False) is False
        assert config.getbool('bool_no', '...') is None
        assert config.getbool('bool_true', False) is True
        assert config.getbool('bool_false', True) is False

    def test_get_int(self):
        d = {'int_1': 1, 'int_str_1': '1', 'int_none': '...'}
        config = BaseConfig(values=d)
        assert config.getint('int_1') == 1
        assert config.getint('int_str_1') == 1
        assert config.getint('int_none') is None
        assert config.getint('int_no') is None
        assert config.getint('int_1', 0) == 1
        assert config.getint('int_none', 0) is None
        assert config.getint('int_no', 0) == 0

    def test_get_float(self):
        d = {'float_1.1': 1.1, 'float_str_1.1': '1.1', 'float_none': '...'}
        config = BaseConfig(values=d)
        assert config.getfloat('float_1.1') == 1.1
        assert config.getfloat('float_str_1.1') == 1.1
        assert config.getfloat('float_none') is None
        assert config.getfloat('float_no') is None
        assert config.getfloat('float_1.1', 0) == 1.1
        assert config.getfloat('float_none', 0) is None
        assert config.getfloat('float_no', 0) == 0

    def test_get_list(self):
        d = {'list': [1, 2], 'tuple': (1, 2), 'single': 1, 'list_str': '1,2'}
        config = BaseConfig(values=d)
        assert config.getlist('list') == [1, 2]
        assert config.getlist('tuple') == [1, 2]
        assert config.getlist('single') == [1]
        assert config.getlist('list_str') == ['1', '2']
        assert config.getlist('list', [1]) == [1, 2]
        assert config.getlist('no_such_list') is None
        assert config.getlist('no_such_list', [1]) == [1]

    def test_set(self):
        config = BaseConfig()
        config.set('key', 'value')
        assert len(config) == 1 and config['key'] == 'value'

        config.set('key', 'value2')
        assert config['key'] == 'value2'

        config.set('key2', 'value')
        assert len(config) == 2 and config['key2'] == 'value'

    def test_set_item(self):
        config = BaseConfig()
        config['key'] = 'value'
        assert len(config) == 1 and config['key'] == 'value'

        config['key'] = 'value2'
        assert config['key'] == 'value2'

        config['key2'] = 'value'
        assert len(config) == 2 and config['key2'] == 'value'

    def test_update(self):
        config = BaseConfig()
        config.update({'key': 'value'})
        assert len(config) == 1 and config['key'] == 'value'

        config.update({'key': 'value2', 'key2': 'value'})
        assert len(config) == 2 and config['key'] == 'value2' and config['key2'] == 'value'

    def test_update_by_base_config(self):
        c1 = BaseConfig()
        c1.set('k1', 'c1_k1')
        c2 = BaseConfig({'k1': 'c2_k1', 'k2': 'c2_k2'})
        c2.set('k3', 'c2_k3')
        c1.update(c2)
        assert len(c1) == 3
        assert c1['k1'] == 'c2_k1'
        assert c1['k2'] == 'c2_k2'
        assert c1['k3'] == 'c2_k3'

    def test_copy(self):
        c1 = BaseConfig()
        c1.set('dict', {'k': 'v'})
        c2 = c1.copy()
        c1['dict']['k'] = 'vv'
        assert c2['dict']['k'] == 'v'

    def test_delete(self):
        c = BaseConfig()
        c.set('k1', 'v1')
        c.set('k2', 'v2')
        c.set('k3', 'v3')
        c.delete('k2')
        assert len(c) == 2 and 'k2' not in c
        c.delete('k1')
        assert len(c) == 1 and 'k1' not in c
        del c['k3']
        assert len(c) == 0 and 'k3' not in c


def test_config():
    c = Config()
    assert len(c) > 0
    for k in c:
        assert k in KNOWN_SETTINGS and c.get(k) == KNOWN_SETTINGS[k].value
