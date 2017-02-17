# coding=utf-8

import os
import asyncio
import zipfile

from xpaw.errors import UsageError
from xpaw.rpc import RpcClient
from xpaw.commands import Command
from xpaw import helpers


class TaskCommand(Command):
    @property
    def syntax(self):
        return "<project_dir>"

    @property
    def name(self):
        return "submit"

    @property
    def short_desc(self):
        return "Submit a crawling task"

    def add_arguments(self, parser):
        Command.add_arguments(self, parser)

        parser.add_argument("project_dir", metavar="project_dir", nargs="?", help="project directory")
        parser.add_argument("-m", "--master-addr", dest="master_addr", metavar="ADDR",
                            help="master address")

    def run(self, args):
        loop = asyncio.get_event_loop()
        master_addr = args.master_addr or self.config.get("master_addr")
        if not args.project_dir:
            raise UsageError()
        project_dir = os.path.abspath(args.project_dir)
        if not os.path.isfile(os.path.join(project_dir, "info.yaml")):
            raise UsageError("Connot find 'info.yaml' in current working directory, "
                             "please assign the task project directory")
        if not os.path.isfile(os.path.join(project_dir, "config.yaml")):
            raise UsageError("Connot find 'config.yaml' in current working directory, "
                             "please assign the task project directory")
        task_info = helpers.load_config_file(os.path.join(project_dir, "info.yaml"))
        zipb = self._compress_dir(project_dir)
        client = RpcClient(master_addr)
        task_id = loop.run_until_complete(client.create_task(task_info, zipb))
        print("Please remember the task ID: {0}".format(task_id))
        print("Task description: {0}".format(task_info.get("description")))

    @staticmethod
    def _compress_dir(dir):
        zipf = os.path.join(os.path.dirname(dir), "{0}.zip".format(os.path.basename(dir)))
        with zipfile.ZipFile(zipf, "w", zipfile.ZIP_DEFLATED) as fz:
            for root, dirs, files in os.walk(dir):
                for file in files:
                    fz.write("%s/%s" % (root, file))
        with open(zipf, "rb") as f:
            zipb = f.read()
        os.remove(zipf)
        return zipb
