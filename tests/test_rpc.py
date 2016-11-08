# coding=utf-8

import asyncio
import threading

import pytest

from xpaw.rpc import RpcServer, RpcClient
from xpaw.errors import RpcError

from .helpers import wait_server_start


@pytest.fixture(scope="function")
def server_without_loop(request):
    def handle(*args, **kw):
        pass

    def run():
        asyncio.set_event_loop(loop)
        server = RpcServer("0.0.0.0:7350")
        server.register_function(handle)
        server.serve_forever()
        try:
            loop.run_forever()
        except Exception:
            pass
        finally:
            loop.close()

    def stop_loop():
        loop.call_soon_threadsafe(loop.stop)

    loop = asyncio.new_event_loop()
    t = threading.Thread(target=run)
    t.start()
    wait_server_start("127.0.0.1:7350")
    request.addfinalizer(stop_loop)


def test_start_server_without_loop(server_without_loop):
    client = RpcClient("127.0.0.1:7350")
    assert client.handle() is None


@pytest.fixture(scope="class")
def rpc_server(request):
    def handle(_host, *args, **kw):
        assert _host == "127.0.0.1"
        return args, kw

    async def async_handle(_host, *args, **kw):
        assert _host == "127.0.0.1"
        return args, kw

    def divide_zero(x):
        return x / 0

    def return_none(*args, **kw):
        return None

    def handle_error(loop, context):
        pass

    def run():
        try:
            loop.run_forever()
        except Exception:
            pass
        finally:
            loop.close()

    def stop_loop():
        loop.call_soon_threadsafe(loop.stop)

    loop = asyncio.new_event_loop()
    loop.set_exception_handler(handle_error)
    server = RpcServer("0.0.0.0:7351", loop=loop)
    server.register_function(handle, "rpc.handle")
    server.register_function(async_handle, "rpc.async_handle")
    server.register_function(divide_zero)
    server.register_function(return_none)
    server.serve_forever()
    t = threading.Thread(target=run)
    t.start()
    wait_server_start("127.0.0.1:7351")
    request.addfinalizer(stop_loop)


@pytest.fixture(scope="class")
def rpc_client():
    return RpcClient("127.0.0.1:7351")


class TestRpc:
    rpc_addr = "127.0.0.1:7351"

    def test_call_function(self, rpc_server, rpc_client):
        async def _test():
            async_rpc_client = RpcClient(self.rpc_addr, loop=loop)
            res = await async_rpc_client.rpc.handle(0, "str", dict={"key": "value"})
            assert res == ((0, "str"), {"dict": {"key": "value"}})

        assert rpc_client.rpc.handle(0, "str", dict={"key": "value"}) == ((0, "str"), {"dict": {"key": "value"}})
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_test())

    def test_call_async_function(self, rpc_server, rpc_client):
        async def _test():
            async_rpc_client = RpcClient(self.rpc_addr, loop=loop)
            res = await async_rpc_client.rpc.async_handle(0, "str", dict={"key": "value"})
            assert res == ((0, "str"), {"dict": {"key": "value"}})

        assert rpc_client.rpc.async_handle(0, "str", dict={"key": "value"}) == ((0, "str"), {"dict": {"key": "value"}})
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_test())

    def test_raise_error(self, rpc_server, rpc_client):
        async def _test():
            async_rpc_client = RpcClient(self.rpc_addr, loop=loop)
            with pytest.raises(ZeroDivisionError):
                await async_rpc_client.divide_zero(1)

        with pytest.raises(ZeroDivisionError):
            rpc_client.divide_zero(1)
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_test())

    def test_method_not_found(self, rpc_server, rpc_client):
        async def _test():
            async_rpc_client = RpcClient(self.rpc_addr, loop=loop)
            with pytest.raises(RpcError):
                await async_rpc_client.handle()

        with pytest.raises(RpcError):
            rpc_client.handle()
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_test())

    def test_return_none(self, rpc_server, rpc_client):
        async def _test():
            async_rpc_client = RpcClient(self.rpc_addr, loop=loop)
            res = async_rpc_client.return_none()
            await res is None

        assert rpc_client.return_none() is None
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_test())
