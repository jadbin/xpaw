# coding=utf-8

import os

import yaml

from xpaw.errors import UsageError
from xpaw import cli


class Command:
    @property
    def description(self):
        return "Set/Get CLI configuration."

    def add_arguments(self, parser):
        parser.add_argument("-G", "--get-all", dest="get_all", action="store_true",
                            help="print all of configuration values")
        parser.add_argument("-g", "--get", dest="get", metavar="K",
                            help="print the configuration value")
        parser.add_argument("-s", "--set", dest="set", metavar="K V", nargs=2,
                            help="set the configuration value")
        parser.add_argument("-u", "--unset", dest="unset", metavar="K",
                            help="unset the configuration value")
        parser.add_argument("-U", "--unset-all", dest="unset_all", action="store_true",
                            help="unset all of configuration values")

    def run(self, args):
        if args.get_all:
            for k, v in cli.config.items():
                print("{0}: {1}".format(k, v))
        elif args.get:
            k = self._format_key(args.get)
            print("{0}: {1}".format(k.replace("_", "-"), cli.config.get(k)))
        elif args.set:
            k, v = args.set
            k = self._format_key(k)
            config = self._load_config()
            config[k] = v
            self._save_config(config)
            print("{0}: {1}".format(k, v))
        elif args.unset:
            k = self._format_key(args.unset)
            config = self._load_config()
            if k in config:
                del config[k]
                self._save_config(config)
        elif args.unset_all:
            if os.path.isfile(cli.CONFIG_FILE):
                os.remove(cli.CONFIG_FILE)
        else:
            raise UsageError()

    @staticmethod
    def _format_key(k):
        return k.lower().replace("-", "_")

    @staticmethod
    def _load_config():
        config = {}
        try:
            with open(cli.CONFIG_FILE, "r", encoding="utf-8") as f:
                config = yaml.load(f)
        except Exception:
            pass
        return config

    @staticmethod
    def _save_config(config):
        try:
            with open(cli.CONFIG_FILE, "w", encoding="utf-8") as f:
                yaml.dump(config, f)
        except Exception:
            pass
