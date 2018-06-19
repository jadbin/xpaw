# coding=utf-8

import os
from os.path import exists, join, abspath, isfile, isdir, basename
from shutil import move, copy2, copystat, ignore_patterns
from datetime import datetime
import logging.config

from .errors import UsageError
from .config import Config
from .utils import string_camelcase, render_templatefile
from .version import __version__
from .cluster import LocalCluster
from .utils import configure_logging
from . import utils

log = logging.getLogger(__name__)


class Command:
    def __init__(self):
        self.config = Config()
        self.exitcode = 0

    @property
    def name(self):
        return ""

    @property
    def syntax(self):
        return ""

    @property
    def short_desc(self):
        return ""

    @property
    def long_desc(self):
        return self.short_desc

    def add_arguments(self, parser):
        pass

    def process_arguments(self, args):
        pass

    def run(self, args):
        raise NotImplementedError


class CrawlCommand(Command):
    @property
    def syntax(self):
        return "[OPTIONS] <PATH>"

    @property
    def name(self):
        return "crawl"

    @property
    def short_desc(self):
        return "Start to crawl web pages"

    def add_arguments(self, parser):
        parser.add_argument("path", metavar="PATH", nargs="?", help="source code path")
        parser.add_argument('-d', '--daemon', dest='daemon', action='store_true',
                            help='run in daemon mode')
        parser.add_argument("-l", "--log-level", dest="log_level", metavar="LEVEL",
                            help="log level")
        parser.add_argument("--log-file", dest="log_file", metavar="FILE",
                            help="log file")
        parser.add_argument("-s", "--set", dest="set", action="append", default=[], metavar="NAME=VALUE",
                            help="set/override setting (can be repeated)")

    def process_arguments(self, args):
        if not args.path:
            raise UsageError()
        if args.daemon is not None:
            self.config.set('daemon', args.daemon)
        if args.log_level is not None:
            self.config.set("log_level", args.log_level)
        if args.log_file is not None:
            self.config.set('log_file', args.log_file)
        try:
            self.config.update(dict(x.split("=", 1) for x in args.set))
        except ValueError:
            raise UsageError("Invalid -s value, use -s NAME=VALUE", print_help=False)

    def run(self, args):
        if not isfile(join(args.path, "setup.cfg")):
            self.exitcode = 1
            print("Error: Cannot find 'setup.cfg' in {}".format(abspath(args.path)))
            return

        if self.config.getbool('daemon'):
            utils.be_daemon()
        configure_logging("xpaw", self.config)
        cluster = LocalCluster(args.path, self.config)
        cluster.start()


_ignore_file_type = ignore_patterns("*.pyc")


class InitCommand(Command):
    def __init__(self):
        super().__init__()

        self.steps_total = 0
        self.steps_count = 0

    @property
    def syntax(self):
        return "<DIR>"

    @property
    def name(self):
        return "init"

    @property
    def short_desc(self):
        return "Initialize a crawling project"

    def add_arguments(self, parser):
        parser.add_argument("project_dir", metavar="DIR", nargs="?", help="project directory")

    def process_arguments(self, args):
        if args.project_dir:
            if not exists(args.project_dir):
                os.mkdir(args.project_dir, mode=0o775)

    def run(self, args):
        if not args.project_dir:
            raise UsageError()

        project_dir = abspath(args.project_dir)
        project_name = basename(project_dir)

        if exists(join(project_dir, "setup.cfg")):
            self.exitcode = 1
            print("Error: setup.cfg already exists in {}".format(project_dir))
            return

        self._init_project(args.project_dir, project_name)

    def _init_project(self, project_dir, project_name):
        self._copytree(join(self.config["templates_dir"], "project"), project_dir)
        move(join(project_dir, "module"), join(project_dir, project_name))
        self._render_files(project_dir,
                           lambda f: render_templatefile(f, version=__version__,
                                                         datetime_now=datetime.now().strftime("%b %d %Y %H:%M:%S"),
                                                         project_name=project_name,
                                                         ProjectName=string_camelcase(project_name)))

        print("New project '{}', created in:".format(project_name,
                                                     self.config["templates_dir"]))
        print("    {}".format(abspath(project_dir)))

    def _copytree(self, src, dst):
        if not exists(dst):
            os.makedirs(dst)
        copystat(src, dst)
        names = os.listdir(src)
        ignored_names = _ignore_file_type(src, names)
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


class VersionCommand(Command):
    @property
    def name(self):
        return "version"

    @property
    def short_desc(self):
        return "Print the version"

    def run(self, args):
        print("xpaw version {}".format(__version__))
