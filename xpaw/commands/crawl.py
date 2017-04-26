# coding=utf-8

from os.path import join, isfile, abspath
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

    def run(self, args):
        if not args.project_dir:
            raise UsageError()
        if not isfile(join(args.project_dir, "config.yaml")):
            self.exitcode = 1
            print("Error: Connot find 'config.yaml' in {}".format(abspath(args.project_dir)))
            return
        
        configure_logging("xpaw", self.config)
        cluster = LocalCluster(args.project_dir, self.config)
        cluster.start()
