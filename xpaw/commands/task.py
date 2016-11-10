# coding=utf-8

import os
import asyncio
import zipfile

import yaml

from xpaw.errors import UsageError
from xpaw.rpc import RpcClient
from xpaw import cli


class Command:
    @property
    def description(self):
        return "Control tasks."

    def add_arguments(self, parser):
        commands = ["submit", "start", "stop", "finish", "remove", "get-info", "get-progress", "get-tasks"]
        parser.add_argument("command", metavar="command", choices=commands, nargs="?",
                            help="available values: {0}".format(", ".join(commands)))
        parser.add_argument("-m", "--master-rpc-addr", dest="master_rpc_addr", metavar="ADDR",
                            help="the RPC address of master")
        parser.add_argument("-i", "--id", dest="id", metavar="ID",
                            help="the ID of a specific task")
        parser.add_argument("-p", "--project", dest="project", metavar="DIR",
                            help="the directory of a task project")

    def run(self, args):
        def _check_master(func):
            def wrapper(*a, **kw):
                if not master_rpc_addr:
                    raise UsageError("Must assign the RPC address of master")
                return func(*a, **kw)

            return wrapper

        def _check_id(func):
            def wrapper(*a, **kw):
                if not task_id:
                    raise UsageError("Must assign the task ID")
                return func(*a, **kw)

            return wrapper

        @_check_master
        def _create():
            if not project:
                project_dir = os.getcwd()
                if not os.path.isfile(os.path.join(project_dir, "info.yaml")):
                    raise UsageError("Connot find 'info.yaml' in current working directory, "
                                     "please assign the task project directory")
                if not os.path.isfile(os.path.join(project_dir, "config.yaml")):
                    raise UsageError("Connot find 'config.yaml' in current working directory, "
                                     "please assign the task project directory")
            else:
                project_dir = os.path.abspath(project)
            task_info = self._load_config(os.path.join(project_dir, "info.yaml"))
            zipb = self._compress_dir(project_dir)
            client = RpcClient(master_rpc_addr)
            task_id = loop.run_until_complete(client.create_task(task_info, zipb))
            print("Please remember the task ID: {0}".format(task_id))
            print("Task description: {0}".format(task_info.get("description")))

        @_check_master
        @_check_id
        def _start():
            client = RpcClient(master_rpc_addr)
            loop.run_until_complete(client.start_task(task_id))

        @_check_master
        @_check_id
        def _stop():
            client = RpcClient(master_rpc_addr)
            loop.run_until_complete(client.stop_task(task_id))

        @_check_master
        @_check_id
        def _finish():
            client = RpcClient(master_rpc_addr)
            loop.run_until_complete(client.finish_task(task_id))

        @_check_master
        @_check_id
        def _remove():
            client = RpcClient(master_rpc_addr)
            loop.run_until_complete(client.remove_task(task_id))

        @_check_master
        @_check_id
        def _get_info():
            client = RpcClient(master_rpc_addr)
            info = loop.run_until_complete(client.get_task_info(task_id))
            print("Task information: {0}".format(info))

        @_check_master
        @_check_id
        def _get_progress():
            client = RpcClient(master_rpc_addr)
            progress = loop.run_until_complete(client.get_task_progress(task_id))
            print("Task progress: {0}".format(progress))

        @_check_master
        def _get_tasks():
            client = RpcClient(master_rpc_addr)
            tasks = loop.run_until_complete(client.get_running_tasks())
            print("Running tasks: {0}".format(tasks))

        loop = asyncio.get_event_loop()
        master_rpc_addr = args.master_rpc_addr or cli.config.get("master_rpc_addr")
        task_id = args.id
        project = args.project
        cmd = args.command
        if cmd == "submit":
            _create()
        elif cmd == "start":
            _start()
        elif cmd == "stop":
            _stop()
        elif cmd == "finish":
            _finish()
        elif cmd == "remove":
            _remove()
        elif cmd == "get-info":
            _get_info()
        elif cmd == "get-progress":
            _get_progress()
        elif cmd == "get-tasks":
            _get_tasks()
        else:
            raise UsageError()

    @staticmethod
    def _load_config(file):
        with open(file, "r", encoding="utf-8") as f:
            d = yaml.load(f)
            return d

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
