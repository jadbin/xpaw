# coding=utf-8

import logging

from . import utils
from . import events

log = logging.getLogger(__name__)


class SetDupeFilter:
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
        h = utils.load_from_dump_dir('dupe_filter', self._dump_dir)
        if h:
            self._hash = h

    def close(self):
        utils.dump_to_dir('dupe_filter', self._dump_dir, self._hash)
