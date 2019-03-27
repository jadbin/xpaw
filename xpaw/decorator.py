# coding=utf-8


def every(hours=None, minutes=None, seconds=None):
    def wrapper(func):
        func.cron_job = True
        func.cron_tick = hours * 3600 + minutes * 60 + seconds
        return func

    if hours is None and minutes is None and seconds is None:
        raise ValueError('At least one of the parameters (hours, minutes and seconds) is not none')
    if hours is None:
        hours = 0
    if minutes is None:
        minutes = 0
    if seconds is None:
        seconds = 0
    return wrapper
