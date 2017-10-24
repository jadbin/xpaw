# coding=utf-8

import re
import cgi
import hashlib


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


def request_fingerprint(request):
    sha1 = hashlib.sha1()
    sha1.update(to_types(request.method))
    sha1.update(to_types(str(request.url)))
    sha1.update(request.body or b'')
    return sha1.hexdigest()


def to_types(data, encoding=None):
    if isinstance(data, bytes):
        return data
    if isinstance(data, str):
        return data.encode(encoding or "utf-8")
    raise TypeError("Need bytes or str, got {}".format(type(data).__name__))
