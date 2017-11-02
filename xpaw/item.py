# coding=utf-8

from collections import MutableMapping


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
        self._values = {}
        for k, v in kwargs.items():
            self[k] = v

    def __getitem__(self, key):
        return self._values[key]

    def __setitem__(self, key, value):
        if key in self.fields:
            self._values[key] = value
        else:
            raise KeyError(key)

    def __delitem__(self, key):
        del self._values[key]

    def __len__(self):
        return len(self._values)

    def __iter__(self):
        return iter(self._values)

    def keys(self):
        return self._values.keys()

    def __repr__(self):
        return repr(dict(self))

    def copy(self):
        return self.__class__(**self._values)
