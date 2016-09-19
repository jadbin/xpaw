# coding=utf-8

import pytest
from aiohttp.helpers import parse_mimetype

from xpaw.selector import Selector


class TestSelector:
    def test_first_and_last(self):
        html = """<li>a</li><div><ul><li>b</li><li>c</li></ul></div><ul><li>d</li></ul>"""
        s = Selector(html)
        assert s.select("//li/text()").first.value == "a"
        assert s.select("//li/text()").last.value == "d"
        assert s.select("//div").select(".//li/text()").first.value == "b"
        assert s.select("//div").select(".//li/text()").last.value == "c"

    def test_attribute_selection(self):
        html = """<div style=display:none><a href="http://example.com/" target=_blank></div>"""
        s = Selector(html)
        assert s.select("//a/@href").first.value == "http://example.com/"
        assert s.select("//a").select("@target").first.value == "_blank"
        assert s.select("//div/@style").first.value == "display:none"

    def test_text_selection(self):
        html = """<div><p>expression: <var>x</var>+<var>y</var>=<var>z</var></p></div>"""
        s = Selector(html)
        assert s.select("//var[last()-1]/text()").first.value == "y"
        assert s.select("//var/text()").value == ["x", "y", "z"]
        assert s.select("//p").first.value == "<p>expression: <var>x</var>+<var>y</var>=<var>z</var></p>"

    def test_encoding_detection(self):
        html = "<html lang=en><title>测试</title><meta charset=utf-8><meta http-equiv=Content-Type content='text/html; charset=gbk' /></html>"
        body = html.encode("gbk")
        with pytest.raises(UnicodeDecodeError):
            s = Selector(body.decode("utf-8"))
        s = Selector(body.decode("ascii", errors="ignore"))
        assert s.select("//meta/@charset").first.value == "utf-8"
        content_type = s.select("//meta[@http-equiv='Content-Type']").select("@content").first.value
        assert content_type == "text/html; charset=gbk"
        mtype, stype, _, params = parse_mimetype(content_type)
        assert mtype == "text" and stype == "html" and params.get("charset") == "gbk"

    def test_wrong_arguments(self):
        html = b"<html></html>"
        with pytest.raises(TypeError):
            s = Selector(html)
        with pytest.raises(ValueError):
            s = Selector()

    def test_wrong_xpath(self):
        html = "<ul><li>a</li><li>b</li></ul>"
        s = Selector(html)
        assert s.select("/li").value == []
        assert s.select("//li/text()").select("/a") == []
