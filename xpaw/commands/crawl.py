# coding=utf-8

import os
import logging.config

from xpaw.errors import UsageError
from xpaw.commands import Command
from xpaw.cluster import LocalCluster
from xpaw.utils.log import configure_logging

log = logging.getLogger(__name__)


class CrawlCommand(Command):
    @property
    def syntax(self):
        return "<project_dir>"

    @property
    def name(self):
        return "crawl"

    @property
    def short_desc(self):
        return "Start to crawl web pages"

    def add_arguments(self, parser):
        Command.add_arguments(self, parser)

        parser.add_argument("project_dir", metavar="project_dir", nargs="?", help="project directory")

    def process_arguments(self, args):
        Command.process_arguments(self, args)

        if not args.project:
            raise UsageError()
        if not os.path.isfile(os.path.join(args.project, "config.yaml")):
            raise UsageError("Connot find 'config.yaml' in current working directory, "
                             "please assign the task project directory")

    def run(self, args):
        configure_logging(self.config)
        cluster = LocalCluster(args.project)
        cluster.start()
