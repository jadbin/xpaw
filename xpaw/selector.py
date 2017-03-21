# coding=utf-8

from lxml import etree


class Selector:
    def __init__(self, html=None, root=None):
        if html is not None:
            if not isinstance(html, str):
                raise TypeError("'html' argument should be of type {}".format(str))
            root = etree.HTML(html)
        elif root is None:
            raise ValueError("Selector needs either 'html' or 'root' argument")
        self._root = root

    def xpath(self, xpath):
        try:
            res = self._root.xpath(xpath, smart_strings=False)
        except Exception:
            return SelectorList([])
        if not isinstance(res, list):
            res = [res]
        return SelectorList([self.__class__(root=i) for i in res])

    @property
    def html(self):
        try:
            return etree.tostring(self._root, encoding="unicode", method="html", with_tail=False)
        except TypeError:
            return str(self._root)

    @property
    def text(self):
        try:
            return etree.tostring(self._root, encoding="unicode", method="text", with_tail=False)
        except TypeError:
            return str(self._root)


class SelectorList(list):
    def __getitem__(self, item):
        obj = super().__getitem__(item)
        return self.__class__(obj) if isinstance(item, slice) else obj

    def xpath(self, xpath):
        res = self.__class__()
        for i in self:
            res += i.xpath(xpath)
        return res

    @property
    def html(self):
        return [i.html for i in self]

    @property
    def text(self):
        return [i.text for i in self]
