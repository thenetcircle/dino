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

from activitystreams import parse as as_parser
from functools import lru_cache
from datetime import datetime
from flask import request

import logging
import traceback

from dino.rest.resources.base import BaseResource
from dino.exceptions import NoSuchRoomException
from dino.exceptions import NoSuchChannelException
from dino.exceptions import NoSuchUserException
from dino import environ
from dino import utils

logger = logging.getLogger(__name__)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class KickResource(BaseResource):
    def __init__(self):
        super(KickResource, self).__init__()
        self.request = request

    def do_post(self):
        is_valid, msg, json = self.validate_json()
        if not is_valid:
            logger.error('invalid json: %s' % msg)
            return dict()

        if json is None:
            return 'no json in request'

        if not isinstance(json, dict):
            return 'need a dict of user-room keys'

        output = dict()
        for private_user_id, room_id in json.items():
            try:
                channel_id = utils.get_channel_for_room(room_id)
            except NoSuchRoomException:
                logger.error('no such room when trying to kick user %s for room %s' % (private_user_id, room_id))
                logger.error(traceback.format_exc())
                continue

            try:
                room_name = utils.get_room_name(room_id)
            except NoSuchChannelException:
                logger.error('no such channel when trying to kick user %s for room %s' % (private_user_id, room_id))
                logger.error(traceback.format_exc())
                continue

            try:
                user_id = environ.env.db.get_private_room(private_user_id)[0]
                user_name = utils.get_user_name_for(private_user_id)
            except NoSuchUserException:
                logger.error('no such user when trying to kick: %s' % private_user_id)
                logger.error(traceback.format_exc())
                continue

            data = {
                'target': {
                    'id': room_id,
                    'displayName': room_name,
                    'url': '/chat'
                },
                'object': {
                    'id': user_id,
                    'url': channel_id,
                    'displayName': user_name
                },
                'verb': 'kick',
                'actor': {
                    'id': '0',
                    'displayName': 'admin'
                }
            }
            activity = as_parser(data)
            environ.env.observer.emit('on_kick', (data, activity))
        return output

    def validate_json(self):
        try:
            return True, None, self.request.get_json(silent=False)
        except Exception as e:
            logger.error('error: %s' % str(e))
            logger.exception(traceback.format_exc())
            return False, 'invalid json in request', None
