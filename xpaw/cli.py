# coding=utf-8

import os
import sys
import argparse

import yaml

from xpaw.errors import UsageError
from xpaw import helpers

USAGE = """usage: xpaw [command] [arguments ...]

optional commands:
  config   get/set the CLI configuration
  crawl    start to crawl web pages
  start    start modules
  task     control tasks
  version  print the version"""

DEFAULT_CONFIG = {
    "log_level": "INFO",
    "log_format": "%(asctime)s %(name)s: [%(levelname)s] %(message)s",
    "log_datefmt": "%b/%d/%Y %H:%M:%S"
}

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".xpawcli")

config = {}
try:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = yaml.load(f)
except Exception:
    pass
for k, v in DEFAULT_CONFIG.items():
    config.setdefault(k, v)

logger = {
    "version": 1,
    "loggers": {
        "xpaw": {
            "level": config.get("log_level"),
            "handlers": ["console"]
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default"
        }
    },
    "formatters": {
        "default": {
            "format": config.get("log_format"),
            "datefmt": config.get("log_datefmt")
        }
    }
}


def main(argv=None):
    if argv is None:
        argv = sys.argv
    if len(argv) <= 1:
        print(USAGE)
        sys.exit(0)
    cmd = argv[1]
    del argv[1]
    try:
        cls = helpers.load_object("xpaw.commands.{0}.Command".format(cmd))
    except Exception:
        print(USAGE)
        print("")
        print("xpaw: error: {0} is not a command".format(cmd))
        sys.exit(2)
    command = cls()
    parser = argparse.ArgumentParser()
    parser.prog = "xpaw {0}".format(cmd)
    parser.description = command.description
    command.add_arguments(parser)
    args = parser.parse_args(args=argv[1:])
    try:
        command.run(args)
    except UsageError as e:
        parser.print_help()
        if str(e):
            print("")
            print("{0}: error: {1}".format(parser.prog, e))
        sys.exit(2)
