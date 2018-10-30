# coding=utf-8

from lxml import etree, cssselect

_text_type_config = {
    'html': {
        'parser_cls': etree.HTMLParser,
        'tostring_method': 'html',
        'css_translator': cssselect.LxmlHTMLTranslator()
    },
    'xml': {
        'parser_cls': etree.XMLParser,
        'tostring_method': 'xml',
        'css_translator': cssselect.LxmlTranslator()
    }
}


def _get_text_type(text_type):
    if text_type in _text_type_config:
        return text_type
    raise ValueError('Invalid text type: {}'.format(text_type))


def create_root_node(text, parser_cls):
    return etree.fromstring(text, parser=parser_cls())


class Selector:
    def __init__(self, text=None, root=None, text_type='html'):
        self.type = _get_text_type(text_type)
        c = _text_type_config[self.type]
        self._parser_cls = c['parser_cls']
        self._tostring_method = c['tostring_method']
        self._css_translator = c['css_translator']
        if text is not None:
            if not isinstance(text, str):
                raise TypeError("'text' argument must be str")
            root = create_root_node(text, parser_cls=self._parser_cls)
        if root is None:
            raise ValueError("Needs either text or root argument")
        self.root = root

    def xpath(self, xpath, **kwargs):
        kwargs.setdefault('smart_strings', False)
        res = self.root.xpath(xpath, **kwargs)
        if not isinstance(res, list):
            res = [res]
        return SelectorList([self.__class__(root=i) for i in res])

    def css(self, css, **kwargs):
        xpath = self._css_translator.css_to_xpath(css)
        return self.xpath(xpath, **kwargs)

    @property
    def string(self):
        try:
            return etree.tostring(self.root, encoding="unicode", method=self._tostring_method, with_tail=False)
        except TypeError:
            return str(self.root)

    @property
    def text(self):
        try:
            return etree.tostring(self.root, encoding="unicode", method="text", with_tail=False)
        except TypeError:
            return str(self.root)

    def attr(self, name):
        res = self.xpath('@' + name)
        if len(res) > 0:
            return res[0].text


class SelectorList(list):
    def __getitem__(self, item):
        obj = super().__getitem__(item)
        return self.__class__(obj) if isinstance(item, slice) else obj

    def xpath(self, xpath, **kwargs):
        res = self.__class__()
        for i in self:
            res += i.xpath(xpath, **kwargs)
        return res

    def css(self, css, **kwargs):
        res = self.__class__()
        for i in self:
            res += i.css(css, **kwargs)
        return res

    @property
    def string(self):
        return [i.string for i in self]

    @property
    def text(self):
        return [i.text for i in self]

    def attr(self, name):
        return [i.attr(name) for i in self]
