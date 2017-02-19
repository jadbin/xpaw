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

        # TODO initialize project

    def _read_project_module_name(self):
        print('({}/{}) What is the base name of your project module? (project)'.format(self.steps_count,
                                                                                       self.steps_total))
        self.steps_count += 1
        module_name = input().strip()
        if not module_name:
            module_name = "project"
        return module_name
