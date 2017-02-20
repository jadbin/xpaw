# coding=utf-8

import os
from os.path import exists, join, abspath, isdir
from shutil import move, copy2, copystat, ignore_patterns

from xpaw.commands import Command
from xpaw.errors import UsageError
from xpaw.utils.template import string_camelcase, render_templatefile

IGNORE = ignore_patterns("*.pyc")


class InitCommand(Command):
    def __init__(self):
        super().__init__()

        self.steps_total = 1
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
            if not exists(args.project_dir):
                os.mkdir(args.project_dir, mode=0o775)

    def run(self, args):
        if not args.project_dir:
            raise UsageError()

        if exists(join(args.project_dir, "config.yaml")):
            self.exitcode = 1
            print("Error: config.yaml already exists in {}".format(abspath(args.project_dir)))
            return

        # project name
        project_name = self._read_project_name()

        self._init_project(args.project_dir, project_name)

    def _read_project_name(self):
        print('({}/{}) What is the name of your project? (project)'.format(self.steps_count,
                                                                           self.steps_total))
        self.steps_count += 1
        project_name = input().strip()
        if not project_name:
            project_name = "project"
        return project_name

    def _init_project(self, project_dir, project_name):
        self._copytree(join(self.config["templates_dir"], "project"), project_dir)
        print(join(project_dir, "module"), join(project_dir, project_name))
        move(join(project_dir, "module"), join(project_dir, project_name))
        self._render_files(project_dir,
                           lambda f: render_templatefile(f, project_name=project_name,
                                                         ProjectName=string_camelcase(project_name)))

    def _copytree(self, src, dst):
        if not exists(dst):
            os.makedirs(dst)
        copystat(src, dst)
        names = os.listdir(src)
        ignored_names = IGNORE(src, names)
        for name in names:
            if name in ignored_names:
                continue
            srcname = join(src, name)
            dstname = join(dst, name)
            if isdir(srcname):
                self._copytree(srcname, dstname)
            else:
                copy2(srcname, dstname)

    def _render_files(self, src, render):
        names = os.listdir(src)
        for name in names:
            srcname = join(src, name)
            if isdir(srcname):
                self._render_files(srcname, render)
            else:
                render(srcname)
