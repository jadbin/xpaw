# coding=utf-8

from xpaw.errors import UsageError
from xpaw.config import Config


class Command:
    def __init__(self):
        self.config = Config()
        self.exitcode = 0

    @property
    def name(self):
        return ""

    @property
    def syntax(self):
        return ""

    @property
    def short_desc(self):
        return ""

    @property
    def long_desc(self):
        return self.short_desc

    def add_arguments(self, parser):
        parser.add_argument("-s", "--set", action="append", default=[], metavar="NAME=VALUE",
                            help="set/override setting (may be repeated)")
        parser.add_argument("-l", "--log-level", dest="log_level", metavar="LEVEL",
                            help="log level")

    def process_arguments(self, args):
        # setting
        try:
            self.config.update(dict(x.split("=", 1) for x in args.set), priority="cmdline")
        except ValueError:
            raise UsageError("Invalid -s value, use -s NAME=VALUE", print_help=False)

        # logger
        if args.log_level:
            self.config.set("log_level", args.loglevel, priority="cmdline")

    def run(self, args):
        raise NotImplementedError
