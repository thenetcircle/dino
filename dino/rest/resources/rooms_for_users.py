from datetime import datetime

from dino.exceptions import NoSuchRoomException
from flask import request

import logging

from dino.utils import b64e
from dino.utils.decorators import timeit
from dino.rest.resources.base import BaseResource
from dino import environ

logger = logging.getLogger(__name__)


class RoomsForUsersResource(BaseResource):
    def __init__(self):
        super(RoomsForUsersResource, self).__init__()
        self.last_cleared = datetime.utcnow()
        self.request = request

    def _do_get(self, user_id):
        output = list()
        channel_ids = dict()
        channel_names = dict()

        rooms = environ.env.db.rooms_for_user(user_id)

        for room_id, room_name in rooms.items():
            try:
                if room_id in channel_ids:
                    channel_id = channel_ids[room_id]
                else:
                    channel_id = environ.env.db.channel_for_room(room_id)
                    channel_ids[room_id] = channel_id

                if channel_id in channel_names:
                    channel_name = channel_names[channel_id]
                else:
                    channel_name = environ.env.db.get_channel_name(channel_id)
                    channel_names[channel_id] = channel_name

                output.append({
                    'room_id': room_id,
                    'room_name': b64e(room_name),
                    'channel_id': channel_id,
                    'channel_name': b64e(channel_name)
                })
            except NoSuchRoomException:
                # can ignore, already deleted or old cache value
                pass

        return output

    def do_get_with_params(self, user_id):
        return self._do_get(user_id)

    @timeit(logger, 'on_rest_rooms_for_users')
    def do_get(self):
        is_valid, msg, json = self.validate_json(self.request, silent=False)
        if not is_valid:
            logger.error('invalid json: %s' % msg)
            return dict()

        if 'users' not in json:
            return dict()
        logger.debug('GET request: %s' % str(json))

        output = dict()
        for user in json['users']:
            output[user] = self.do_get_with_params(user)
        return output

    def _get_lru_method(self):
        return self.do_get_with_params

    def _get_last_cleared(self):
        return self.last_cleared

    def _set_last_cleared(self, last_cleared):
        self.last_cleared = last_cleared
