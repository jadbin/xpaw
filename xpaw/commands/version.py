# coding=utf-8


import xpaw
from xpaw.commands import Command


class VersionCommand(Command):
    @property
    def name(self):
        return "version"

    @property
    def description(self):
        return "Print the version"

    def add_arguments(self, parser):
        pass

    def run(self, args):
        print("xpaw version {0}".format(xpaw.__version__))
