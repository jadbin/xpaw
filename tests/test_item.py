# coding=utf-8

import pytest

from xpaw.item import Item, Field


class MyItem(Item):
    f1 = Field()
    f2 = Field()


def test_item():
    with pytest.raises(KeyError):
        MyItem(f3='v3')
    item = MyItem(f1='v1')
    assert len(item) == 1 and 'f1' in item
    assert item['f1'] == 'v1'
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
