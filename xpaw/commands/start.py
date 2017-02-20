# coding=utf-8

import os

from xpaw.errors import UsageError
from xpaw.master import Master
from xpaw.fetcher import Fetcher
from xpaw.agent import Agent
from xpaw.commands import Command
from xpaw.utils.log import configure_logging
from xpaw.utils.config import load_config_file


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
        parser.add_argument("-c", "--config-file", dest="config_file", metavar="FILE",
                            help="configuration file")
        parser.add_argument("-d", "--data-dir", dest="data_dir", metavar="DIR",
                            help="data directory")

    def process_arguments(self, args):
        Command.process_arguments(self, args)

        if args.data_dir:
            data_dir = os.path.abspath(args.data_dir)
            self.config["data_dir"] = data_dir

        # configuration file
        if args.config_file:
            config = load_config_file(args.config_file)
            for k, v in config.items():
                self.config[k] = v

    def run(self, args):
        name = args.module
        if not name:
            raise UsageError()
        configure_logging(self.config)
        if name == "master":
            master = Master(self.config)
            master.start()
        elif name == "fetcher":
            fetcher = Fetcher(self.config)
            fetcher.start()
        elif name == "agent":
            agent = Agent(self.config)
            agent.start()
        else:
            raise UsageError()
