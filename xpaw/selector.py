# coding=utf-8

from lxml import etree


class Selector:
    def __init__(self, html=None, root=None):
        if html is not None:
            if not isinstance(html, str):
                raise TypeError("'html' argument should be of type {0}".format(str))
            root = etree.HTML(html)
        elif root is None:
            raise ValueError("Selector needs either 'html' or 'root' argument")
        self._root = root

    def select(self, xpath):
        try:
            res = self._root.xpath(xpath, smart_strings=False)
        except Exception:
            return SelectorList([])
        if not isinstance(res, list):
            res = [res]
        return SelectorList([self.__class__(root=i) for i in res])

    @property
    def value(self):
        try:
            return etree.tostring(self._root, encoding="unicode", method="html")
        except TypeError:
            return str(self._root)


class SelectorList(list):
    def __getitem__(self, item):
        obj = super().__getitem__(item)
        return self.__class__(obj) if isinstance(item, slice) else obj

    def select(self, xpath):
        res = self.__class__()
        for i in self:
            res += i.select(xpath)
        return res

    @property
    def value(self):
        return [i.value for i in self]
