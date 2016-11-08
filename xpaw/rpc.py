# coding=utf-8

import pickle
import inspect
import asyncio
import logging

import aiohttp
from aiohttp import web

from xpaw.errors import RpcError

log = logging.getLogger(__name__)


class RpcServer:
    def __init__(self, server_listen, *, loop=None):
        self._server_listen = server_listen
        self._funcs = {}
        self._loop = loop or asyncio.get_event_loop()
        self._server = None

    def register_function(self, func, name=None):
        if name is None:
            name = func.__name__
        self._funcs[name] = func

    def serve_forever(self):
        log.debug("Start RPC server on '{0}'".format(self._server_listen))
        app = web.Application(logger=log, loop=self._loop)
        for f in self._funcs:
            log.debug("Register function '{0}'".format(f))
            resource = app.router.add_resource("/{0}".format(f))
            resource.add_route("POST", lambda r, func=self._funcs[f]: self._handle(r, func))
        host, port = self._server_listen.split(":")
        port = int(port)
        self._loop.run_until_complete(
            self._loop.create_server(app.make_handler(access_log=None), host, port))

    async def _handle(self, request, func):
        body = await request.read()
        data = pickle.loads(body)
        args, kwargs = data[0], data[1]
        host = None
        peername = request.transport.get_extra_info("peername")
        if peername:
            host, _ = peername
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
            return web.Response(body=pickle.dumps(e),
                                status=500)
        else:
            return web.Response(body=pickle.dumps(res))


class RpcClient:
    def __init__(self, server_addr, *, timeout=10, loop=None):
        if not server_addr.startswith("http://"):
            server_addr = "http://{0}".format(server_addr)
        if server_addr.endswith("/"):
            server_addr = server_addr[:-1]
        self._server_addr = server_addr
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
        data = [args if args else [], kw if kw else {}]
        async with aiohttp.ClientSession(loop=self._loop) as session:
            async with session.post("{0}/{1}".format(self._server_addr, func_name),
                                    data=pickle.dumps(data),
                                    timeout=self._timeout) as resp:
                body = await resp.read()
                if resp.status == 200:
                    return pickle.loads(body)
                elif resp.status == 500:
                    raise pickle.loads(body)
                elif resp.status == 404:
                    raise RpcError("The method '{0}' is not found".format(func_name))
                else:
                    raise RpcError("Unknown RPC error")


class _Method:
    def __init__(self, send, name):
        self._send = send
        self._name = name

    def __getattr__(self, name):
        return _Method(self._send, "{0}.{1}".format(self._name, name))

    def __call__(self, *args, **kw):
        return self._send(self._name, args, kw)
