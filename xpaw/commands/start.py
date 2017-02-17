# coding=utf-8

import os

from xpaw.errors import UsageError
from xpaw.master import Master
from xpaw.fetcher import Fetcher
from xpaw.agent import Agent
from xpaw.commands import Command


class StartCommand(Command):
    @property
    def syntax(self):
        return "<module>"

    @property
    def name(self):
        return "start"

    @property
    def short_desc(self):
        return "Start to run modules"

    def add_arguments(self, parser):
        Command.add_arguments(self, parser)

        modules = ["master", "fetcher", "agent"]
        parser.add_argument("module", metavar="module", choices=modules, nargs="?",
                            help="available values: {0}".format(", ".join(modules)))
        parser.add_argument("-d", "--data-dir", dest="data_dir", metavar="DIR",
                            help="data directory")

    def process_arguments(self, args):
        Command.process_arguments(self, args)

        if args.data_dir:
            data_dir = os.path.abspath(args.data_dir)
            self.config["data_dir"] = data_dir

    def run(self, args):
        name = args.module
        if not name:
            raise UsageError()

        if name == "master":
            master = Master.from_config(self.config)
            master.start()
        elif name == "fetcher":
            fetcher = Fetcher.from_config(self.config)
            fetcher.start()
        elif name == "agent":
            agent = Agent.from_config(self.config)
            agent.start()
        else:
            raise UsageError()
