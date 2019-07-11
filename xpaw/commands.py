# coding=utf-8

import os
from os.path import exists, join, abspath, isfile, isdir, basename, dirname, split, splitext
from shutil import move, copy, copymode, ignore_patterns
import logging
from importlib import import_module
import sys
import inspect

from .errors import UsageError
from .utils import string_camelcase, render_template_file, load_config, iter_settings
from . import __version__
from .run import run_crawler
from .spider import Spider

log = logging.getLogger(__name__)


class Command:
    def __init__(self):
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


def _import_spider(file):
    file = abspath(file)
    d, f = split(file)
    m, ext = splitext(f)
    if ext != '.py':
        raise UsageError('{} is not a python module'.format(file))
    if d not in sys.path:
        sys.path.append(d)
    module = import_module(m)
    for v in vars(module).values():
        if inspect.isclass(v) and issubclass(v, Spider) and v.__module__ == module.__name__:
            return v
    raise UsageError('Cannot find spider in {}'.format(file))


class Option:
    def __init__(self, name=None, cli=None, metavar=None, default=None, action=None, type=None, nargs=None,
                 short_desc=None):
        self.name = name
        self.cli = cli
        self.metavar = metavar
        self.default = default
        self.action = action
        self.type = type
        self.nargs = nargs
        self.short_desc = short_desc

    def add_argument(self, parser):
        if self.cli is None:
            return
        args = tuple(self.cli)
        kwargs = {'dest': self.name, 'help': self.short_desc}
        if self.metavar is not None:
            kwargs['metavar'] = self.metavar
        if self.action is not None:
            kwargs['action'] = self.action
        if self.type is not None:
            kwargs['type'] = self.type
        if self.nargs is not None:
            kwargs['nargs'] = self.nargs
        parser.add_argument(*args, **kwargs)


class CrawlCommand(Command):
    def __init__(self):
        super().__init__()
        self.config = {}
        self.options = [
            Option(name='daemon', cli=['-d', '--daemon'], action='store_true', short_desc='run in daemon mode'),
            Option(name='log_level', cli=['-l', '--log-level'], metavar='LEVEL', short_desc='log level'),
            Option(name='log_file', cli=['--log-file'], metavar='FILE', short_desc='log file'),
            Option(name='pid_file', cli=['--pid-file'], metavar='FILE', short_desc='PID file')]

    @property
    def syntax(self):
        return "[options] <PATH>"

    @property
    def name(self):
        return "crawl"

    @property
    def short_desc(self):
        return "Start to crawl web pages"

    def add_arguments(self, parser):
        parser.add_argument("path", metavar="PATH", nargs=1, help="project directory or spider file")
        parser.add_argument('-c', '--config', dest='config', metavar='FILE',
                            help='configuration file')
        for s in self.options:
            s.add_argument(parser)
        parser.add_argument("-s", "--set", dest="set", action="append", default=[], metavar="NAME=VALUE",
                            help="set/override setting (can be repeated)")

    def process_arguments(self, args):
        args.path = args.path[0]
        if args.config is not None:
            c = load_config(args.config)
            for k, v in iter_settings(c):
                self.config[k] = v
        try:
            self.config.update(dict(x.split("=", 1) for x in args.set))
        except ValueError:
            raise UsageError("Invalid -s value, use -s NAME=VALUE")
        for s in self.options:
            v = getattr(args, s.name)
            if v is not None:
                self.config[s.name] = v

    def run(self, args):
        if isfile(args.path):
            spider = _import_spider(args.path)
            self.config['spider'] = spider
            run_crawler(proj_dir=None, config=self.config)
        elif isdir(args.path):
            run_crawler(proj_dir=args.path, config=self.config)
        else:
            raise UsageError('Cannot find {}'.format(args.path))


_ignore_file_type = ignore_patterns("*.pyc")


class InitCommand(Command):
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
        parser.add_argument("project_dir", metavar="DIR", nargs=1,
                            help="project directory, the last part of the path is the project name")
        parser.add_argument('--templates', metavar='DIR', dest='templates',
                            default=join(dirname(__file__), 'templates'),
                            help='the directory of templates')

    def process_arguments(self, args):
        args.project_dir = args.project_dir[0]
        if not exists(args.project_dir):
            os.mkdir(args.project_dir, mode=0o775)

    def run(self, args):
        project_dir = abspath(args.project_dir)
        project_name = basename(project_dir)
        templates_dir = abspath(args.templates)
        module_dir = join(project_dir, project_name)
        self._copytree(join(templates_dir, 'project'), project_dir)
        move(join(project_dir, "module"), module_dir)
        self._render_files(project_dir,
                           lambda f: render_template_file(f, version=__version__,
                                                          project_name=project_name,
                                                          ProjectName=string_camelcase(project_name)))

        print("New project '{}' created in {}".format(project_name, abspath(project_dir)))

    def _copytree(self, src, dst):
        if not exists(dst):
            os.makedirs(dst, 0o755)
        copymode(src, dst)
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
                copy(srcname, dstname)

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
