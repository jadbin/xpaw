# coding=utf-8


import xpaw
from xpaw.commands import Command


class VersionCommand(Command):
    @property
    def name(self):
        return "version"

    @property
    def short_desc(self):
        return "Print the version"

    def add_arguments(self, parser):
        Command.add_arguments(self, parser)

    def run(self, args):
        print("xpaw version {}".format(xpaw.__version__))
