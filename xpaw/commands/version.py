# coding=utf-8


import xpaw


class Command:
    @property
    def description(self):
        return "Print the version."

    def add_arguments(self, parser):
        pass

    def run(self, args):
        print("xpaw version {0}".format(xpaw.__version__))
