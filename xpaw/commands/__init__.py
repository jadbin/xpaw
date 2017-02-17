# coding=utf-8

import logging

from xpaw import helpers


class Command:
    DEFAULT_CONFIG = {
        "log_level": "INFO",
        "log_format": "%(asctime)s %(name)s: [%(levelname)s] %(message)s",
        "log_datefmt": "%b/%d/%Y %H:%M:%S"
    }

    def __init__(self):
        self.config = {}
        for k, v in self.DEFAULT_CONFIG.items():
            self.config.setdefault(k, v)

    @property
    def name(self):
        raise NotImplementedError

    @property
    def description(self):
        raise NotImplementedError

    def add_arguments(self, parser):
        parser.add_argument("-c", "--config", dest="config_file", metavar="DIR",
                            help="data directory")
        parser.add_argument("-l", "--log-level", dest="log_level", metavar="LEVEL",
                            help="log level")

    def process_arguments(self, args):
        # configuration
        if args.config_file:
            config = helpers.load_config_file(args.config_file)
            for k, v in config:
                self.config[k] = v

        # logger
        if args.log_level:
            self.config["log_level"] = args.log_level
        logger = logging.getLogger("xpaw")
        logger.setLevel(self.config["log_level"])
        log_stream_handler = logging.StreamHandler()
        log_stream_handler.setLevel(self.config["log_level"])
        log_formatter = logging.Formatter(self.config["log_format"], self.config["log_datefmt"])
        log_stream_handler.setFormatter(log_formatter)

    def run(self, args):
        raise NotImplementedError
