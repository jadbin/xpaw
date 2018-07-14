# coding=utf-8

import logging
from os.path import join, isfile

from . import utils
from . import events

log = logging.getLogger(__name__)


class HashDupeFilter:
    def __init__(self, dump_dir=None):
        self._dump_dir = dump_dir
        self._hash = set()

    @classmethod
    def from_cluster(cls, cluster):
        config = cluster.config
        dupe_filter = cls(dump_dir=utils.get_dump_dir(config))
        cluster.event_bus.subscribe(dupe_filter.open, events.cluster_start)
        cluster.event_bus.subscribe(dupe_filter.close, events.cluster_shutdown)
        return dupe_filter

    def is_duplicated(self, request):
        if request.dont_filter:
            return False
        h = utils.request_fingerprint(request)
        if h in self._hash:
            log.debug("Find the request %s is duplicated", request)
            return True
        self._hash.add(h)
        return False

    def clear(self):
        self._hash.clear()

    def open(self):
        if self._dump_dir:
            file = join(self._dump_dir, 'dupe_filter')
            if isfile(file):
                with open(file, 'r') as f:
                    for h in f:
                        self._hash.add(h.rstrip())

    def close(self):
        if self._dump_dir:
            with open(join(self._dump_dir, 'dupe_filter'), 'w') as f:
                for h in self._hash:
                    f.write(h + '\n')
