# coding=utf-8

from collections import MutableMapping

from . import config


class BaseItem:
    """
    Super class for all items.
    """


class Field(dict):
    """
    Field consist of metadata
    """


class Item(MutableMapping, BaseItem):
    def __init__(self, **kwargs):
        self.fields = {}
        for k in dir(self):
            v = getattr(self, k)
            if isinstance(v, Field):
                self.fields[k] = v
        self.values = {}
        for k, v in kwargs.items():
            self[k] = v

    def __getitem__(self, key):
        if key not in self:
            return None
        v = self.values[key]
        t = self.fields[key].get('type')
        if t:
            if isinstance(t, str):
                if t == 'str':
                    v = str(v)
                elif t == 'int':
                    v = config.getint(v)
                elif t == 'float':
                    v = config.getfloat(v)
                elif t == 'bool':
                    v = config.getbool(v)
                else:
                    raise ValueError('Unsupported item filed type: {}'.format(t))
            else:
                v = t(v)
        return v

    def __contains__(self, name):
        return name in self.values

    def __setitem__(self, key, value):
        if key in self.fields:
            self.values[key] = value
        else:
            raise KeyError(key)

    def __delitem__(self, key):
        del self.values[key]

    def __len__(self):
        return len(self.values)

    def __iter__(self):
        return iter(self.values)

    def keys(self):
        return self.values.keys()

    def __repr__(self):
        return repr(dict(self))

    def copy(self):
        return self.__class__(**self.values)
