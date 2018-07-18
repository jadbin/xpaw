# coding=utf-8

import pytest

from xpaw.item import Item, Field


class FooItem(Item):
    f1 = Field()
    f2 = Field()


def test_item():
    with pytest.raises(KeyError):
        FooItem(f3='v3')
    item = FooItem(f1='v1')
    assert len(item) == 1 and 'f1' in item
    assert item['f1'] == 'v1' and item['f2'] is None
    item['f2'] = 'v2'
    assert item.keys() == {'f1', 'f2'}
    s = {}
    for k in item:
        s[k] = item[k]
    assert s == {'f1': 'v1', 'f2': 'v2'}
    assert len(item) == 2 and 'f2' in item
    assert item['f2'] == 'v2'
    item_copy = item.copy()
    del item['f2']
    assert len(item) == 1 and 'f2' not in item
    assert len(item_copy) == 2 and item_copy['f1'] == 'v1' and item_copy['f2'] == 'v2'
    item['f2'] = 'new_v2'
    assert item['f2'] == 'new_v2'
    repr_str = repr(item)
    assert repr_str == "{'f1': 'v1', 'f2': 'new_v2'}" or repr_str == "{'f2': 'new_v2', 'f1': 'v1'}"


class FieldTypeItem(Item):
    none_field = Field()
    str_field = Field(type='str')
    int_field = Field(type='int')
    float_field = Field(type='float')
    bool_field = Field(type='bool')
    func_field = Field(type=int)
    error_field = Field(type='error type')


def test_field_type():
    item = FieldTypeItem(str_field=1, int_field='1', float_field='1', bool_field='1', func_field='1', error_field='1')
    assert item['none_field'] is None
    assert item['str_field'] == '1'
    assert isinstance(item['int_field'], int) and item['int_field'] == 1
    assert isinstance(item['float_field'], float) and item['float_field'] == 1
    assert item['bool_field'] is True
    assert isinstance(item['func_field'], int) and item['func_field'] == 1
    with pytest.raises(ValueError):
        print(item['error_field'])
