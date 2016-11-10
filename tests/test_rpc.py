# coding=utf-8

import asyncio
import threading

import pytest

from xpaw.rpc import RpcServer, RpcClient
from xpaw.errors import RpcError

from .helpers import wait_server_start


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
    server.start()
    t = threading.Thread(target=run)
    t.start()
    wait_server_start("127.0.0.1:7351")
    request.addfinalizer(stop_loop)


class TestRpc:
    rpc_addr = "127.0.0.1:7351"

    def test_call_function(self, rpc_server):
        async def _test():
            async_rpc_client = RpcClient(self.rpc_addr, loop=loop)
            res = await async_rpc_client.rpc.handle(0, "str", pi=3.141592657, dict={"list": [0, 1.0, "2"]})
            assert res == ((0, "str"), {"pi": 3.141592657, "dict": {"list": [0, 1.0, "2"]}})

        loop = asyncio.new_event_loop()
        loop.run_until_complete(_test())

    def test_call_async_function(self, rpc_server):
        async def _test():
            async_rpc_client = RpcClient(self.rpc_addr, loop=loop)
            res = await async_rpc_client.rpc.async_handle(0, "str", pi=3.141592657, dict={"list": [0, 1.0, "2"]})
            assert res == ((0, "str"), {"pi": 3.141592657, "dict": {"list": [0, 1.0, "2"]}})

        loop = asyncio.new_event_loop()
        loop.run_until_complete(_test())

    def test_raise_error(self, rpc_server):
        async def _test():
            async_rpc_client = RpcClient(self.rpc_addr, loop=loop)
            with pytest.raises(RpcError):
                await async_rpc_client.divide_zero(1)

        loop = asyncio.new_event_loop()
        loop.run_until_complete(_test())

    def test_method_not_found(self, rpc_server):
        async def _test():
            async_rpc_client = RpcClient(self.rpc_addr, loop=loop)
            with pytest.raises(RpcError):
                await async_rpc_client.handle()

        loop = asyncio.new_event_loop()
        loop.run_until_complete(_test())

    def test_return_none(self, rpc_server):
        async def _test():
            async_rpc_client = RpcClient(self.rpc_addr, loop=loop)
            res = async_rpc_client.return_none()
            await res is None

        loop = asyncio.new_event_loop()
        loop.run_until_complete(_test())
