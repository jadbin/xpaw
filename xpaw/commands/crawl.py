# coding=utf-8

import os
import logging.config

from xpaw.errors import UsageError
from xpaw.commands import Command
from xpaw.cluster import LocalCluster

log = logging.getLogger(__name__)


class CrawlCommand(Command):
    @property
    def name(self):
        return "crawl"

    @property
    def description(self):
        return "Start to crawl web pages"

    def add_arguments(self, parser):
        Command.add_arguments(self, parser)

        parser.add_argument("-p", "--project", dest="project", metavar="DIR",
                            help="task project directory")

    def process_arguments(self, args):
        Command.process_arguments(self, args)

        if not args.project:
            args = os.getcwd()
        args.project = os.path.abspath(args.project)
        if not os.path.isfile(os.path.join(args.project, "config.yaml")):
            raise UsageError("Connot find 'config.yaml' in current working directory, "
                             "please assign the task project directory")

    def run(self, args):
        cluster = LocalCluster(args.project)
        cluster.start()
