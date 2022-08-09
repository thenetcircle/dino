import logging
from functools import lru_cache

from flask import request

from datetime import datetime
from dino import environ
from dino.rest.resources.base import BaseResource
from dino.utils.decorators import timeit

logger = logging.getLogger(__name__)


class DumpCacheResource(BaseResource):
    def __init__(self):
        super(DumpCacheResource, self).__init__()
        self.last_cleared = datetime.utcnow()
        self.request = request
        self.namespace = "/ws"

    def _get_lru_method(self):
        return self.get_cache

    def _get_last_cleared(self):
        return self.last_cleared

    def _set_last_cleared(self, last_cleared):
        self.last_cleared = last_cleared

    @lru_cache()
    def get_cache(self):
        # mock cache doesn't have in-memory cache
        if hasattr(environ.env.cache, "cache"):
            return environ.env.cache.cache.vals

    @timeit(logger, "on_rest_dump_cache_cache")
    def do_get(self):
        return self.get_cache()
