# coding=utf-8

import os
import asyncio
import threading

import pytest

from xpaw.cli import main
from xpaw.rpc import RpcServer
from xpaw.master import Master
from xpaw.fetcher import Fetcher
from xpaw.agent import Agent
from xpaw.config import Config

from .helpers import wait_server_start


class StartData:
    def __init__(self, tmpdir):
        self.func_name = set()
        self.config_file = os.path.join(tmpdir, "config.yaml")
        self.config = {"master_addr": "0.0.0.0:7310",
                       "downloader_clients": 100,
                       "spider_headers": None}
        self.data_dir = os.path.join(tmpdir, "data")
        self.config["data_dir"] = self.data_dir


@pytest.fixture(scope="function")
def start_data(request, monkeypatch, tmpdir):
    class M:
        def start(self):
            d.func_name.remove("master_start")

    def master_from_config(config):
        assert isinstance(config, Config)
        d.func_name.remove("master_from_config")
        return M()

    class F:
        def start(self):
            d.func_name.remove("fetcher_start")

    def fetcher_from_config(config):
        assert isinstance(config, Config)
        d.func_name.remove("fetcher_from_config")
        return F()

    class A:
        def start(self):
            d.func_name.remove("agent_start")

    def agent_from_config(config):
        assert isinstance(config, Config)
        d.func_name.remove("agent_from_config")
        return A()

    monkeypatch.setattr(Master, "from_config", master_from_config)
    monkeypatch.setattr(Fetcher, "from_config", fetcher_from_config)
    monkeypatch.setattr(Agent, "from_config", agent_from_config)
    request.addfinalizer(lambda: monkeypatch.undo())
    d = StartData("{0}".format(tmpdir))
    with open(d.config_file, "wb") as f:
        for i, j in d.config.items():
            f.write("{0}: {1}\n".format(i, "" if j is None else j).encode("utf-8"))
    return d


def test_start_master(start_data):
    d = start_data
    d.func_name.add("master_start")
    d.func_name.add("master_from_config")
    main(argv=["xpaw", "start", "master", "--config-file", d.config_file, "--data-dir", d.data_dir])
    assert len(d.func_name) == 0


def test_start_fetcher(start_data):
    d = start_data
    d.func_name.add("fetcher_start")
    d.func_name.add("fetcher_from_config")
    main(argv=["xpaw", "start", "fetcher", "--config-file", d.config_file, "--data-dir", d.data_dir])
    assert len(d.func_name) == 0


def test_start_agent(start_data):
    d = start_data
    d.func_name.add("agent_start")
    d.func_name.add("agent_from_config")
    main(
        argv=["xpaw", "start", "agent", "--config-file", d.config_file, "--data-dir", d.data_dir])
    assert len(d.func_name) == 0


class TaskData:
    def __init__(self):
        def handle_error(loop, context):
            pass

        self.serve_addr = "0.0.0.0:7360"
        self.rpc_addr = "127.0.0.1:7360"
        self.task_id = "0123456789abcdef"
        self.task_info = {"status": 0, "description": "task_description", "create_time": None, "finish_time": None}
        self.func_name = set()
        self.loop = asyncio.new_event_loop()
        self.loop.set_exception_handler(handle_error)


@pytest.fixture(scope="module")
def task_data(request):
    def create_task(task_info, task_config_zip):
        assert task_info == d.task_info and isinstance(task_config_zip, bytes)
        d.func_name.remove("create_task")

    def start_task(task_id):
        assert task_id == d.task_id
        d.func_name.remove("start_task")

    def stop_task(task_id):
        assert task_id == d.task_id
        d.func_name.remove("stop_task")

    def finish_task(task_id):
        assert task_id == d.task_id
        d.func_name.remove("finish_task")

    def remove_task(task_id):
        assert task_id == d.task_id
        d.func_name.remove("remove_task")

    def get_task_info(task_id):
        assert task_id == d.task_id
        d.func_name.remove("get_task_info")

    def get_task_progress(task_id):
        assert task_id == d.task_id
        d.func_name.remove("get_task_progress")

    def get_running_tasks():
        d.func_name.remove("get_running_tasks")

    def run():
        try:
            d.loop.run_forever()
        except Exception:
            pass
        finally:
            d.loop.close()

    def stop_loop():
        d.loop.call_soon_threadsafe(d.loop.stop)

    d = TaskData()
    server = RpcServer(d.serve_addr, loop=d.loop)
    server.register_function(create_task)
    server.register_function(start_task)
    server.register_function(stop_task)
    server.register_function(finish_task)
    server.register_function(remove_task)
    server.register_function(get_task_info)
    server.register_function(get_task_progress)
    server.register_function(get_running_tasks)
    server.start()
    t = threading.Thread(target=run)
    t.start()
    wait_server_start(d.rpc_addr)
    request.addfinalizer(stop_loop)
    return d


class TestTaskCommand:
    def test_start_task(self, task_data):
        d = task_data
        d.func_name.add("start_task")
        main(argv=["xpaw", "task", "start", d.task_id, "--master-addr", d.rpc_addr])
        assert len(d.func_name) == 0

    def test_stop_task(self, task_data):
        d = task_data
        d.func_name.add("stop_task")
        main(argv=["xpaw", "task", "stop", d.task_id, "--master-addr", d.rpc_addr])
        assert len(d.func_name) == 0

    def test_finish_task(self, task_data):
        d = task_data
        d.func_name.add("finish_task")
        main(argv=["xpaw", "task", "finish", d.task_id, "--master-addr", d.rpc_addr])
        assert len(d.func_name) == 0

    def test_remove_task(self, task_data):
        d = task_data
        d.func_name.add("remove_task")
        main(argv=["xpaw", "task", "remove", d.task_id, "--master-addr", d.rpc_addr])
        assert len(d.func_name) == 0

    def test_query_task(self, task_data):
        d = task_data
        d.func_name.add("get_task_info")
        d.func_name.add("get_task_progress")
        main(argv=["xpaw", "task", "query", d.task_id, "--master-addr", d.rpc_addr])
        assert len(d.func_name) == 0


class TestSubmitCommand:
    def test_submit_task(self, tmpdir, task_data):
        d = task_data
        project_dir = os.path.join("{0}".format(tmpdir), "project")
        os.mkdir(project_dir, mode=0o775)
        with open(os.path.join(project_dir, "config.yaml"), "wb") as f:
            f.write(b"project_name: 'test'\n")
        with open(os.path.join(project_dir, "info.yaml"), "wb") as f:
            for i, j in d.task_info.items():
                f.write("{0}: {1}\n".format(i, "" if j is None else j).encode("utf-8"))
        d.func_name.add("create_task")
        main(argv=["xpaw", "submit", "{0}".format(project_dir), "--master-addr", d.rpc_addr])
        assert len(d.func_name) == 0
