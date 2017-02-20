# coding=utf-8

import os
import re
import string


def render_templatefile(path, **kwargs):
    if path.endswith(".tmpl"):
        with open(path, "rb") as f:
            raw = f.read().decode("utf-8")

        content = string.Template(raw).substitute(**kwargs)

        render_path = path[:-len(".tmpl")]
        with open(render_path, "wb") as f:
            f.write(content.encode("utf-8"))
        os.remove(path)


CAMELCASE_INVALID_CHARS = re.compile('[^a-zA-Z\d]')


def string_camelcase(s):
    return CAMELCASE_INVALID_CHARS.sub('', s.title())
