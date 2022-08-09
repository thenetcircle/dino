import logging

from flask import request

from dino import environ
from dino.rest.resources.base import BaseResource
from dino.utils.decorators import timeit

logger = logging.getLogger(__name__)


class CacheCleanupResource(BaseResource):
    def __init__(self):
        super(CacheCleanupResource, self).__init__()
        self.request = request
        self.namespace = "/ws"

    @timeit(logger, "on_rest_cache_cleanup")
    def do_post(self):
        # mock cache doesn't have in-memory cache
        if hasattr(environ.env.cache, "cache"):
            environ.env.cache.cache.cleanup()
