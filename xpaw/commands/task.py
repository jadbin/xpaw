# coding=utf-8

import asyncio

from xpaw.errors import UsageError
from xpaw.rpc import RpcClient
from xpaw.commands import Command


class TaskCommand(Command):
    @property
    def syntax(self):
        return "<command> <task_id>"

    @property
    def name(self):
        return "task"

    @property
    def short_desc(self):
        return "Control tasks"

    def add_arguments(self, parser):
        Command.add_arguments(self, parser)

        commands = ["start", "stop", "finish", "remove", "query"]
        parser.add_argument("command", metavar="command", choices=commands, nargs="?",
                            help="available commans: {0}".format(", ".join(commands)))
        parser.add_argument("task_id", metavar="task_id", nargs="?",
                            help="task id")
        parser.add_argument("-m", "--master-addr", dest="master_addr", metavar="ADDR",
                            help="master address")

    def run(self, args):
        loop = asyncio.get_event_loop()
        master_addr = args.master_addr or self.config.get("master_addr")
        task_id = args.task_id
        cmd = args.command
        if cmd == "start":
            client = RpcClient(master_addr)
            loop.run_until_complete(client.start_task(task_id))
        elif cmd == "stop":
            client = RpcClient(master_addr)
            loop.run_until_complete(client.stop_task(task_id))
        elif cmd == "finish":
            client = RpcClient(master_addr)
            loop.run_until_complete(client.finish_task(task_id))
        elif cmd == "remove":
            client = RpcClient(master_addr)
            loop.run_until_complete(client.remove_task(task_id))
        elif cmd == "query":
            client = RpcClient(master_addr)
            info = loop.run_until_complete(client.get_task_info(task_id))
            print("Task information: {0}".format(info))
            progress = loop.run_until_complete(client.get_task_progress(task_id))
            print("Task progress: {0}".format(progress))
        else:
            raise UsageError()
