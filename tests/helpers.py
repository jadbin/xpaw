# coding=utf-8

import time
import socket


def wait_server_start(addr):
    host, port = addr.split(":")
    port = int(port)
    not_ready = True
    while not_ready:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        res = s.connect_ex((host, port))
        s.close()
        if res == 0:
            not_ready = False
        else:
            time.sleep(0.1)
