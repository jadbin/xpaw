# coding=utf-8

import pytest
from aiohttp.helpers import parse_mimetype

from xpaw.selector import Selector


class TestSelector:
    def test_selector_list(self):
        html = """<li>a</li><div><ul><li>b</li><li>c</li></ul></div><ul><li>d</li></ul>"""
        s = Selector(html)
        assert s.select("//li/text()")[0].text == "a"
        assert s.select("//li/text()")[-1].text == "d"
        assert s.select("//div").select(".//li").text[0] == "b"
        assert s.select("//div").select(".//li").text[-1] == "c"

    def test_attribute_selection(self):
        html = """<div style=display:none><a href="http://example.com/" target=_blank></div>"""
        s = Selector(html)
        assert s.select("//a/@href")[0].html == "http://example.com/"
        assert s.select("//a").select("@target")[0].html == "_blank"
        assert s.select("//div/@style")[0].html == "display:none"

    def test_text_selection(self):
        html = """<div><p>expression: <var>x</var>+<var>y</var>=<var>z</var></p></div>"""
        s = Selector(html)
        assert s.select("//var[last()-1]/text()")[0].html == "y"
        assert s.select("//var/text()").html == ["x", "y", "z"]
        assert s.select("//p")[0].html == "<p>expression: <var>x</var>+<var>y</var>=<var>z</var></p>"
        assert s.select("//p")[0].text == "expression: x+y=z"
        assert s.select("//p/text()")[0].html == "expression: "

    def test_encoding_detection(self):
        html = "<html lang=en><head>" \
               "<title>测试</title>" \
               "<meta charset=utf-8>" \
               "<meta http-equiv=Content-Type content='text/html; charset=gbk' />" \
               "</head></html>"
        body = html.encode("gbk")
        with pytest.raises(UnicodeDecodeError):
            s = Selector(body.decode("utf-8"))
        s = Selector(body.decode("ascii", errors="ignore"))
        assert s.select("//meta/@charset")[0].html == "utf-8"
        content_type = s.select("//meta[@http-equiv='Content-Type']").select("@content")[0].html
        assert content_type == "text/html; charset=gbk"
        mtype, stype, _, params = parse_mimetype(content_type)
        assert mtype == "text" and stype == "html" and params.get("charset") == "gbk"

    def test_wrong_arguments(self):
        html = b"<html></html>"
        with pytest.raises(TypeError):
            s = Selector(html)
        with pytest.raises(ValueError):
            s = Selector()

    def test_confused_xpath(self):
        html = "<p>text</p><ul><p>header</p><li>a</li><li>b</li></ul>"
        s = Selector(html)

        assert s.select("/li") == []
        assert s.select("//li") != []

        assert s.select("/ul") == []
        assert s.select("/html/body/ul") != []

        assert s.select("//ul").select("//p")[0].text == "text"
        assert s.select("//ul").select(".//p")[0].text == "header"
        assert s.select("//ul").select("./p")[0].text == "header"
