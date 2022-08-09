import logging

from flask import request

from dino import environ
from dino.rest.resources.base import BaseResource
from dino.utils.decorators import timeit

logger = logging.getLogger(__name__)


class DumpCacheResource(BaseResource):
    def __init__(self):
        super(DumpCacheResource, self).__init__()
        self.request = request
        self.namespace = "/ws"

    @timeit(logger, "on_rest_dump_cache_cache")
    def do_post(self):
        # mock cache doesn't have in-memory cache
        if hasattr(environ.env.cache, "cache"):
            return environ.env.cache.cache.vals
