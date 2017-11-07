# coding=utf-8

import pytest

from xpaw.config import BaseConfig, get_config_priority, ConfigAttribute, Config


def test_get_config_priority():
    assert get_config_priority('default') == 0
    assert get_config_priority('project') == 10
    assert get_config_priority('cmdline') == 20
    with pytest.raises(KeyError):
        get_config_priority('unknown_priority')
    assert get_config_priority(-1) == -1


class TestConfigAttribute:
    def test_set(self):
        c = ConfigAttribute('v', 1)
        assert c.value == 'v' and c.priority == 1
        c.set('v0', 0)
        assert c.value == 'v' and c.priority == 1
        c.set('v1', 1)
        assert c.value == 'v1' and c.priority == 1
        c.set('v2', 2)
        assert c.value == 'v2' and c.priority == 2

    def test_repr(self):
        class C:
            def __init__(self, v):
                self.v = v

            def __repr__(self):
                return str(self.v)

        c = ConfigAttribute(C(1), 0)
        assert repr(c) == '<ConfigAttribute value=1 priority=0>'


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

    def test_get_priority(self):
        config = BaseConfig()
        config.set('default', 'default', priority='default')
        config.set('project', 'project', priority='project')
        config.set('cmdline', 'cmdline', priority='cmdline')
        assert config.getpriority('default') == get_config_priority('default')
        assert config.getpriority('project') == get_config_priority('project')
        assert config.getpriority('cmdline') == get_config_priority('cmdline')
        assert config.getpriority('no_such_key') is None

    def test_set(self):
        config = BaseConfig()
        assert len(config) == 0
        config.set('key', 'value')
        assert len(config) == 1
        assert config.getpriority('key') == get_config_priority('project')

        config.set('key', 'default', priority='default')
        assert config['key'] == 'value' and config.getpriority('key') == get_config_priority('project')
        config.set('key', 'project', priority='project')
        assert config['key'] == 'project' and config.getpriority('key') == get_config_priority('project')
        config.set('key', 'cmdline', priority='cmdline')
        assert config['key'] == 'cmdline' and config.getpriority('key') == get_config_priority('cmdline')

        config.set('key_default', 'value', priority='default')
        assert len(config) == 2
        assert config.getpriority('key_default') == get_config_priority('default')

        config.set('no_key', 'v_no_key', priority='default')
        assert len(config) == 3
        assert config['no_key'] == 'v_no_key' and config.getpriority('no_key') == get_config_priority('default')

        config.set('no_attr', ConfigAttribute('v_no_attr', 0), priority='cmdline')
        assert len(config) == 4
        assert config['no_attr'] == 'v_no_attr' and config.getpriority('no_attr') == 0

    def test_set_item(self):
        config = BaseConfig({'ck': 'ck_v'}, priority='cmdline')
        config['key'] = 'value'
        assert config['key'] == 'value' and config.getpriority('key') == get_config_priority('project')
        config['key'] = 'new_value'
        assert config['key'] == 'new_value' and config.getpriority('key') == get_config_priority('project')
        config['ck'] = 'value'
        assert config['ck'] == 'ck_v' and config.getpriority('ck') == get_config_priority('cmdline')

    def test_update(self):
        config = BaseConfig()
        config.update({'key': 'value'})
        assert config.getpriority('key') == get_config_priority('project')

        config.update({'key': 'default'}, priority='default')
        assert config['key'] == 'value' and config.getpriority('key') == get_config_priority('project')
        config.update({'key': 'project'}, priority='project')
        assert config['key'] == 'project' and config.getpriority('key') == get_config_priority('project')
        config.update({'key': 'cmdline'}, priority='cmdline')
        assert config['key'] == 'cmdline' and config.getpriority('key') == get_config_priority('cmdline')

        config.update({'key_default': 'value'}, priority='default')
        assert config.getpriority('key_default') == get_config_priority('default')

    def test_update_by_base_config(self):
        c1 = BaseConfig()
        c1.set('k1', 'c1_k1', priority='default')
        c1.set('k2', 'c1_k2', priority='project')
        c1.set('k3', 'c1_k3', priority='cmdline')
        c2 = BaseConfig({'k1': 'c2_k1', 'k2': 'c2_k2', 'k3': 'c2_k3'}, priority='project')
        c2.set('k4', 'c2_k4', priority='default')
        c1.update(c2)
        assert len(c1) == 4
        assert c1['k1'] == 'c2_k1' and c1.getpriority('k1') == get_config_priority('project')
        assert c1['k2'] == 'c2_k2' and c1.getpriority('k2') == get_config_priority('project')
        assert c1['k3'] == 'c1_k3' and c1.getpriority('k3') == get_config_priority('cmdline')
        assert c1['k4'] == 'c2_k4' and c1.getpriority('k4') == get_config_priority('default')

    def test_copy(self):
        c1 = BaseConfig()
        c1.set('dict', {'k': 'v'})
        c2 = c1.copy()
        c1['dict']['k'] = 'vv'
        assert c2['dict']['k'] == 'v'

    def test_delete(self):
        c = BaseConfig()
        c.set('k1', 'v1', priority='default')
        c.set('k2', 'v2', priority='project')
        c.set('k3', 'v3', priority='cmdline')
        c.delete('k2', priority='default')
        assert len(c) == 3 and 'k2' in c
        c.delete('k2', priority='project')
        assert len(c) == 2 and 'k2' not in c
        c.set('k1', 'v1', priority='project')
        c.delete('k1', priority='default')
        assert len(c) == 2 and 'k1' in c
        c.delete('k1')
        assert len(c) == 1 and 'k1' not in c
        c.delete('k3')
        assert len(c) == 1 and 'k3' in c
        del c['k3']
        assert len(c) == 0 and 'k3' not in c


def test_config():
    c = Config()
    assert len(c) > 0
    for k in c:
        assert c.getpriority(k) == get_config_priority('default')
