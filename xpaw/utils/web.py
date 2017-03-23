# coding=utf-8

import re
import cgi


def get_encoding_from_header(content_type):
    content_type, params = cgi.parse_header(content_type)
    if "charset" in params:
        return params["charset"]


_charset_re = re.compile(r"""<meta.*?charset=["']*(.+?)["'>]""", flags=re.I)
_pragma_re = re.compile(r"""<meta.*?content=["']*;?charset=(.+?)["'>]""", flags=re.I)
_xml_re = re.compile(r"""^<\?xml.*?encoding=["']*(.+?)["'>]""")


def get_encoding_from_content(content):
    if isinstance(content, bytes):
        content = content.decode("ascii", errors="ignore")
    elif not isinstance(content, str):
        raise ValueError("content should be bytes or str")
    s = _charset_re.search(content)
    if s:
        return s.group(1).strip()
    s = _pragma_re.search(content)
    if s:
        return s.group(1).strip()
    s = _xml_re.search(content)
    if s:
        return s.group(1).strip()
