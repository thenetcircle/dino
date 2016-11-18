#!/usr/bin/env python

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from functools import lru_cache
from datetime import datetime
from flask import request
from dino.utils import b64e

import logging
import traceback

from dino.rest.resources.base import BaseResource
from dino import environ

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class RoomsForUsersResource(BaseResource):
    def __init__(self):
        super(RoomsForUsersResource, self).__init__()
        self.last_cleared = datetime.utcnow()

    def _do_get(self, user_id):
        output = list()
        channel_ids = dict()
        channel_names = dict()

        rooms = environ.env.db.rooms_for_user(user_id)

        for room_id, room_name in rooms.items():
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

        return output

    @lru_cache()
    def do_get_with_params(self, user_id):
        return self._do_get(user_id)

    def do_get(self):
        is_valid, msg, json = self.validate_json()
        if not is_valid:
            logging.error('invalid json: %s' % msg)
            return dict()

        if 'users' not in json:
            return dict()

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

    def validate_json(self):
        try:
            return True, None, request.get_json(silent=False)
        except Exception as e:
            print('error: %s' % str(e))
            print(traceback.format_exc())
            return False, 'invalid json in request', None
