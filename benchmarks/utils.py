# coding=utf-8

import time


def log_time(name):
    def wrapper(func):
        def run(*args, **kwargs):
            start = time.time()
            res = func(*args, **kwargs)
            print('The execution time of {}: {}'.format(name, time.time() - start))
            return res

        return run

    return wrapper
