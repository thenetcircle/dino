from datetime import datetime
from flask import request

import logging

from dino.rest.resources.base import BaseResource
from dino.utils.decorators import timeit
from dino import environ

logger = logging.getLogger(__name__)


class RoomsResource(BaseResource):
    def __init__(self):
        super(RoomsResource, self).__init__()
        self.last_cleared = datetime.utcnow()
        self.request = request

    def _get_lru_method(self):
        return self.do_get_with_params

    def _get_last_cleared(self):
        return self.last_cleared

    def _set_last_cleared(self, last_cleared):
        self.last_cleared = last_cleared

    @timeit(logger, 'on_rest_rooms')
    def do_get(self):
        return environ.env.db.get_all_rooms()
