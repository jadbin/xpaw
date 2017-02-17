# coding=utf-8

from importlib import import_module
from pkgutil import iter_modules

import yaml


def load_object(path):
    dot = path.rindex(".")
    module, name = path[:dot], path[dot + 1:]
    mod = import_module(module)
    return getattr(mod, name)


def walk_modules(path):
    mods = []
    mod = import_module(path)
    mods.append(mod)
    if hasattr(mod, "__path__"):
        for _, subpath, ispkg in iter_modules(mod.__path__):
            fullpath = path + "." + subpath
            if ispkg:
                mods += walk_modules(fullpath)
            else:
                submod = import_module(fullpath)
                mods.append(submod)
    return mods


def load_config_file(file):
    with open(file, "r", encoding="utf-8") as f:
        d = yaml.load(f)
        return d


def dump_config_file(file, config):
    with open(file, "w", encoding="utf-8") as f:
        yaml.dump(config, f)
