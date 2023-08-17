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

import logging
from datetime import datetime

from flask import request

from dino import environ
from dino import utils
from dino.config import ErrorCodes
from dino.exceptions import NoSuchRoomException
from dino.rest.resources.base import BaseResource

logger = logging.getLogger(__name__)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class MutedResource(BaseResource):
    def __init__(self):
        super(MutedResource, self).__init__()
        self.last_cleared = datetime.utcnow()
        self.request = request

    def _get_lru_method(self):
        return self.do_get_with_params

    def _get_last_cleared(self):
        return self.last_cleared

    def _set_last_cleared(self, last_cleared):
        self.last_cleared = last_cleared

    def do_get_with_params(self, user_id):
        return environ.env.db.get_mutes_for_user(user_id)

    def do_get(self):
        is_valid, msg, json = self.validate_json(self.request, silent=True)
        if not is_valid:
            logger.error('invalid json: %s' % msg)
            return dict()

        if json is None:
            return environ.env.db.get_muted_users()

        logger.debug('GET request: %s' % str(json))
        output = dict()

        if 'users' in json:
            for user_id in json['users']:
                output[user_id] = self.do_get_with_params(user_id)

        elif 'room_id' in json:
            output = environ.env.db.get_muted_users_for_room(json['room_id'], encode_response=True)

        elif 'room_name' in json:
            room_name = utils.b64d(json['room_name'])
            try:
                room_id = utils.get_room_id(room_name)
                output = environ.env.db.get_muted_users_for_room(room_id, encode_response=True)
            except NoSuchRoomException:
                logger.error('no such room: %s' % json['room_name'])
                return {
                    "code": ErrorCodes.NO_SUCH_ROOM,
                    "message": "no room exists with name {}".format(room_name)
                }

        return output
