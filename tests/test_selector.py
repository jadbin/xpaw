# coding=utf-8

import pytest
from aiohttp.helpers import parse_mimetype

from xpaw.selector import Selector


class TestXPathSelector:
    def test_selector_list(self):
        html = """<li>a</li><div><ul><li>b</li><li>c</li></ul></div><ul><li>d</li></ul>"""
        s = Selector(html)
        assert s.xpath("//li/text()")[0].text == "a"
        assert s.xpath("//li/text()")[-1].text == "d"
        assert s.xpath("//div").xpath(".//li").text[0] == "b"
        assert s.xpath("//div").xpath(".//li").text[-1] == "c"

    def test_attribute_selection(self):
        html = """<a href="http://example.com/" target=_blank>"""
        s = Selector(html)
        assert s.xpath('//a')[0].xpath('@href')[0].text == 'http://example.com/'
        assert s.xpath("//a/@href")[0].text == "http://example.com/"
        assert s.xpath("//a/@target")[0].text == "_blank"

    def test_text_selection(self):
        html = """<div><p>expression: <var>x</var>+<var>y</var>=<var>z</var></p></div>"""
        s = Selector(html)
        assert s.xpath("//var/text()")[0].text == "x"
        assert s.xpath("//var")[0].text == "x"
        assert s.xpath("//var[last()]").text == ["z"]
        assert s.xpath("//var/text()").text == ["x", "y", "z"]
        assert s.xpath("//var").text == ["x", "y", "z"]
        assert s.xpath("//p")[0].text == "expression: x+y=z"
        assert s.xpath("//p/text()")[0].string == "expression: "

    def test_diff_between_string_and_text(self):
        html = """<div><p>expression: <var>x</var>+<var>y</var>=<var>z</var></p></div>"""
        s = Selector(html)
        assert s.xpath("//var")[0].text == "x"
        assert s.xpath("//var")[0].string == "<var>x</var>"
        assert s.xpath("//var").text == ["x", "y", "z"]
        assert s.xpath("//var").string == ["<var>x</var>", "<var>y</var>", "<var>z</var>"]

    def test_node_selection(self):
        html = """<p></p><p class='primary'>primary</p><p class="minor gray">minor</p>"""
        s = Selector(html)
        primary = s.xpath("//p[@class='primary']")
        assert len(primary) == 1 and primary[0].text == 'primary'
        minor = s.xpath("//p[@class='minor']")
        assert len(minor) == 0
        minor = s.xpath("//p[@class='gray minor']")
        assert len(minor) == 0
        minor = s.xpath("//p[@class='minor gray']")
        assert len(minor) == 1 and minor[0].text == 'minor'
        minor = s.xpath("//p[contains(@class, 'minor')]")
        assert len(minor) == 1 and minor[0].text == 'minor'

    def test_encoding_detection(self):
        html = "<html lang=en><head>" \
               "<title>测试</title>" \
               "<meta charset=gbk>" \
               "<meta http-equiv=Content-Type content='text/html; charset=gbk' />" \
               "</head></html>"
        body = html.encode("gbk")
        with pytest.raises(UnicodeDecodeError):
            Selector(body.decode("utf-8"))
        s = Selector(body.decode("ascii", errors="ignore"))
        assert s.xpath("//meta/@charset")[0].text == "gbk"
        content_type = s.xpath("//meta[@http-equiv='Content-Type']/@content")[0].text
        assert content_type == "text/html; charset=gbk"
        mimetype = parse_mimetype(content_type)
        assert mimetype.type == "text" and mimetype.subtype == "html" and mimetype.parameters.get("charset") == "gbk"

    def test_wrong_arguments(self):
        html = b"<html></html>"
        with pytest.raises(TypeError):
            Selector(html)
        with pytest.raises(ValueError):
            Selector()

    def test_node_context(self):
        html = "<p>header</p><div><p>text</p></div>"
        s = Selector(html)
        assert s.xpath("/p") == []
        assert s.xpath("//p") != []
        assert s.xpath("/html/body/p") != []
        assert s.xpath("//p")[0].text == "header"
        assert s.xpath("//div").xpath("//p")[0].text == "header"
        assert s.xpath("//div").xpath(".//p")[0].text == "text"
        assert s.xpath("//div").xpath("./p")[0].text == "text"


class TestCssSelector:
    def test_selector_list(self):
        html = """<li>a</li><div><ul><li>b</li><li>c</li></ul></div><ul><li>d</li></ul>"""
        s = Selector(html)
        assert s.css("li")[0].text == "a"
        assert s.css("li")[-1].text == "d"
        assert s.css("div li").text[0] == "b"
        assert s.css("div li").text[-1] == "c"

    def test_node_selection(self):
        s = Selector("""<html>
                <body>
                    <h1 class='header'><a href="http://example.com/">example</a></h1>
                    <ul>
                        <li><a class='primary link' href="http://example.com/index">index</a></li>
                        <li><a class='link' href="http://example.com/content">content</a></li>
                    </ul>
                </body>
                </html>""")
        assert s.css('a')[0].text == 'example'
        assert s.css('a[class=link]')[0].text == 'content'
        assert s.css('a[class~=link]')[0].text == 'index'
        assert s.css('ul>a') == []
        assert len(s.css('li>a')) == 2
        assert s.css('ul a')[0].text == 'index'
        assert s.css('ul').css('a')[0].text == 'index'
        assert s.css('li>a:not([class~=primary])')[0].text == 'content'

    def test_attribute_selection(self):
        s = Selector("""<html>
                        <body>
                            <h1 class='header'><a href="http://example.com/">example</a></h1>
                            <ul>
                                <li><a class='primary link' href="http://example.com/">index</a></li>
                                <li><a class='link' href="http://example.com/content">content</a></li>
                            </ul>
                        </body>
                        </html>""")
        assert s.css('h1').xpath('@class')[0].text == 'header'
        assert s.css('li>a[class=link]').xpath('@href')[0].text == 'http://example.com/content'
        assert s.css('h1').attr('class')[0] == 'header'
        assert s.css('h1')[0].attr('class') == 'header'
        assert s.css('li>a').attr('class')[0] == 'primary link'
        assert s.css('li>a').attr('class')[-1] == 'link'
        assert s.css('ul').attr('class') == [None]
        assert s.css('ul')[0].attr('class') is None
        assert s.css('h2').attr('class') == []


class TestXmlText:
    def test_text_selection(self):
        xml = "<xml><p>header</p><div><p>text</p></div></xml>"
        xs = Selector(xml, text_type='xml')
        assert xs.xpath('/p') == []
        assert xs.xpath('//p') != []
        assert xs.xpath('/xml/p') != []
        assert xs.xpath("//p")[0].text == "header"
        assert xs.xpath("//div").xpath("//p")[0].text == "header"
        assert xs.xpath("//div").xpath(".//p")[0].text == "text"
        assert xs.xpath("//div").xpath("./p")[0].text == "text"

    def test_not_xml(self):
        from lxml.etree import XMLSyntaxError
        xml = """expression: <var>x</var>+<var>y</var>=<var>z</var>"""
        with pytest.raises(XMLSyntaxError):
            xs = Selector(xml, text_type='xml')


def test_selection_error():
    xml = """
    <bookstore>
      <book>
        <title lang="eng">Harry Potter</title>
        <price>29.99</price>
      </book>
      <book>
        <title lang="eng">Learning XML</title>
        <price>39.95</price>
      </book>
    </bookstore>"""

    s = Selector(xml, text_type='xml')
    assert s.xpath('/bookstore/book[first()]') == []
    assert s.css('book >> price') == []
