# coding=utf-8

import os
import logging
import logging.config

import yaml

from xpaw.errors import UsageError
from xpaw.master import Master
from xpaw.fetcher import Fetcher
from xpaw.agent import Agent
from xpaw import cli

log = logging.getLogger(__name__)


class Command:
    @property
    def description(self):
        return "Start components."

    def add_arguments(self, parser):
        modules = ["master", "fetcher", "agent"]
        parser.add_argument("module", metavar="module", choices=modules, nargs="?",
                            help="available values: {0}".format(", ".join(modules)))
        parser.add_argument("-c", "--config", dest="config", metavar="FILE",
                            help="the configuration file of this module")
        parser.add_argument("-d", "--data-dir", dest="data_dir", metavar="DIR",
                            help="the directory to store data")
        parser.add_argument("-l", "--logger", dest="logger", metavar="FILE",
                            help="the configuration file of the logger")

    def run(self, args):
        name = args.module
        if not name:
            raise UsageError()
        if not args.config:
            raise UsageError("Must assign the configuration file")
        config = self._load_config(args.config)
        if args.data_dir:
            data_dir = os.path.abspath(args.data_dir)
        else:
            data_dir = os.path.join(os.getcwd(), "data")
        config.setdefault("data_dir", data_dir)
        if args.logger:
            logging.config.dictConfig(self._load_config(args.logger))
        else:
            logging.config.dictConfig(cli.logger)
        if name == "master":
            try:
                master = Master.from_config(config)
                master.start()
            except BaseException:
                log.error("Unhandled exception occurred", exc_info=True)

        elif name == "fetcher":
            try:
                fetcher = Fetcher.from_config(config)
                fetcher.start()
            except BaseException:
                log.error("Unhandled exception occurred", exc_info=True)
        elif name == "agent":
            try:
                agent = Agent.from_config(config)
                agent.start()
            except BaseException:
                log.error("Unhandled exception occurred", exc_info=True)
        else:
            raise UsageError()

    @staticmethod
    def _load_config(file):
        with open(file, "r", encoding="utf-8") as f:
            d = yaml.load(f)
            return d
