# coding=utf-8

import os

from xpaw.commands import Command
from xpaw.errors import UsageError


class InitCommand(Command):
    def __init__(self):
        super(InitCommand, self).__init__()

        self.steps_total = 4
        self.steps_count = 1

    @property
    def syntax(self):
        return "<project_dir>"

    @property
    def name(self):
        return "init"

    @property
    def short_desc(self):
        return "Initialize a crawling project"

    def add_arguments(self, parser):
        Command.add_arguments(self, parser)

        parser.add_argument("project_dir", metavar="project_dir", nargs="?", help="project directory")

    def process_arguments(self, args):
        Command.process_arguments(self, args)

        if args.project_dir:
            if not os.path.exists(args.project_dir):
                os.mkdir(args.project_dir, mode=0o775)

    def run(self, args):
        if not args.project_dir or not os.path.exists(args.project_dir):
            raise UsageError()
        base_dir = os.path.abspath(args.project_dir)

        # project module name
        module_name = self._read_project_module_name()

        # using dedupe
        using_dedupe = self._read_using_dedupe()

        # using proxy
        using_proxy = self._read_using_proxy()

        # retry
        retry = self._read_retry()

        # TODO initialize project

    def _read_project_module_name(self):
        print('({}/{}) What is the base name of your project module? (project)'.format(self.steps_count,
                                                                                       self.steps_total))
        self.steps_count += 1
        module_name = input().strip()
        if not module_name:
            module_name = "project"
        return module_name

    def _read_using_dedupe(self):
        print('({}/{}) Would you like to use MongoDB to deduplicate URL automatically?'
              ' You need set the MongoDB address in the configuration later. (Y/n)'.format(self.steps_count,
                                                                                           self.steps_total))
        self.steps_count += 1
        s = input().strip().lower()
        if s.startswith("n"):
            return False
        return True

    def _read_using_proxy(self):
        print('({}/{}) Would you like to use proxy when send requests?'
              ' You need set the proxy agent address in the configuration later. (Y/n)'.format(self.steps_count,
                                                                                               self.steps_total))
        self.steps_count += 1
        s = input().strip().lower()
        if s.startswith("n"):
            return False
        return True

    def _read_retry(self):
        print('({}/{}) Would you like to retry when fail to send requests?'
              ' You can reset the maximal retry times in the configuration later. (Y/n)'.format(self.steps_count,
                                                                                                self.steps_total))
        self.steps_count += 1
        s = input().strip().lower()
        if s.startswith("n"):
            return False
        return True
