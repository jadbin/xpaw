# coding=utf-8

from importlib import import_module


def load_object(path):
    dot = path.rindex(".")
    module, name = path[:dot], path[dot + 1:]
    mod = import_module(module)
    return getattr(mod, name)
