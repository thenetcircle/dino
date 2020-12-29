from datetime import datetime
from flask import request

import logging

from dino.rest.resources.base import BaseResource
from dino.utils.decorators import timeit
from dino import environ

logger = logging.getLogger(__name__)


class RoomsAclResource(BaseResource):
    def __init__(self):
        super(RoomsAclResource, self).__init__()
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
        all_rooms = environ.env.db.get_all_rooms()
        channel_acls = dict()
        room_acls = dict()

        for room in all_rooms:
            room["users"] = len(environ.env.db.users_in_room(room["id"]))
            room_acls[room["id"]] = environ.env.db.get_all_acls_room(room["id"])

            if room["channel_id"] not in channel_acls:
                channel_acls[room["channel_id"]] = environ.env.db.get_all_acls_channel(room["channel_id"])



        return all_rooms
