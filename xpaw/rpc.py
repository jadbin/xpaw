# coding=utf-8

import pickle
import inspect
import asyncio
import logging

import aiohttp

from xpaw.errors import RpcNotFound, RpcTimeoutError, RpcParsingError

log = logging.getLogger(__name__)


class RpcServer:
    def __init__(self, server_addr, *, loop=None):
        self._server_addr = server_addr
        self._functions = {}
        self._loop = loop or asyncio.get_event_loop()
        self._server = None

    def register_function(self, function, name=None):
        if name is None:
            name = function.__name__
        self._functions[name] = function

    def serve_forever(self):
        host, port = self._server_addr.split(":")
        port = int(port)
        coro = self._loop.create_server(lambda: _RpcServerProtocol(self._handle, self._loop), host, port)
        self._server = self._loop.run_until_complete(coro)

    def shutdown(self):
        if self._server:
            self._loop.call_soon_threadsafe(self._server.close)
            self._server = None

    async def _handle(self, data, *, host=None):
        name, args, kwargs = data.get("name"), data.get("args", ()), data.get("kwargs", {})
        if name not in self._functions:
            return RpcNotFound("The method '{0}' is not found".format(name))
        func = self._functions[name]
        try:
            params = []
            for i in inspect.signature(func).parameters:
                if i == "_host":
                    params.append(host)
                else:
                    break
            res = func(*params, *args, **kwargs)
            if inspect.iscoroutine(res):
                res = await res
        except Exception as e:
            return e
        else:
            return res


class _RpcServerProtocol(asyncio.Protocol):
    def __init__(self, handle, loop):
        self._handle = handle
        self._loop = loop
        self._transport = None
        self._host = None

    def connection_made(self, transport):
        self._transport = transport
        peername = self._transport.get_extra_info("peername")
        if peername:
            self._host, _ = peername

    def data_received(self, data):
        asyncio.ensure_future(self._handle_data(data), loop=self._loop)

    async def _handle_data(self, data):
        try:
            d = pickle.loads(data)
        except Exception:
            res = RpcParsingError("Fail to parse data from client.")
        else:
            res = await self._handle(d, host=self._host)
        self._transport.write(pickle.dumps(res))


class RpcClient:
    def __init__(self, server_addr, *, timeout=20, loop=None):
        self._server_host, port = server_addr.split(":")
        self._server_port = int(port)
        self._timeout = timeout
        if loop is None:
            self._send = self._call
            self._loop = asyncio.new_event_loop()
        else:
            self._send = self._async_call
            self._loop = loop

    def __getattr__(self, name):
        return _Method(self._send, name)

    def _call(self, func_name, args, kw):
        return self._loop.run_until_complete(self._request(func_name, args, kw))

    async def _async_call(self, func_name, args, kw):
        return await self._request(func_name, args, kw)

    async def _request(self, func_name, args, kw):
        semaphore = asyncio.Semaphore(0, loop=self._loop)
        data = {"name": func_name}
        if args:
            data["args"] = args
        if kw:
            data["kwargs"] = kw
        coro = self._loop.create_connection(lambda: _RpcClientProtocol(data, semaphore),
                                            self._server_host,
                                            self._server_port)
        transport, protocol = await coro
        try:
            with aiohttp.Timeout(self._timeout, loop=self._loop):
                await semaphore.acquire()
        except Exception:
            res = RpcTimeoutError()
        else:
            res = protocol.data
        finally:
            transport.close()
        if isinstance(res, Exception):
            raise res
        return res


class _RpcClientProtocol(asyncio.Protocol):
    def __init__(self, call, semaphore):
        self._call = call
        self._semaphore = semaphore
        self._transport = None
        self._data = None

    def connection_made(self, transport):
        self._transport = transport
        transport.write(pickle.dumps(self._call))

    def data_received(self, data):
        try:
            d = pickle.loads(data)
        except Exception:
            self._data = RpcParsingError("Fail to parse data from server.")
        else:
            self._data = d
        finally:
            self._semaphore.release()

    @property
    def data(self):
        return self._data


class _Method:
    def __init__(self, send, name):
        self._send = send
        self._name = name

    def __getattr__(self, name):
        return _Method(self._send, "{0}.{1}".format(self._name, name))

    def __call__(self, *args, **kw):
        return self._send(self._name, args, kw)
