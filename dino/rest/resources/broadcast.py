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

from dino.exceptions import NoSuchRoomException

from dino import environ
from dino import utils
from dino.utils.decorators import timeit
from dino.rest.resources.base import BaseResource

from flask import request

logger = logging.getLogger(__name__)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


def fail(error_message):
    return {
        'status': 'FAIL',
        'message': error_message
    }


class BroadcastResource(BaseResource):
    def __init__(self):
        super(BroadcastResource, self).__init__()
        self.request = request

    @timeit(logger, 'on_rest_broadcast')
    def do_post(self):
        is_valid, msg, json = self.validate_json(self.request, silent=False)
        if not is_valid:
            logger.error('invalid json: %s' % msg)
            raise RuntimeError('invalid json')

        if json is None:
            raise RuntimeError('no json in request')
        if not isinstance(json, dict):
            raise RuntimeError('need a dict')

        logger.debug('POST request: %s' % str(json))

        if 'body' not in json:
            raise RuntimeError('no key [body] in json message')
        if 'verb' not in json:
            raise RuntimeError('no key [verb] in json message')

        body = json.get('body')
        if body is None or len(body.strip()) == 0:
            raise RuntimeError('body may not be blank')
        if not utils.is_base64(body):
            raise RuntimeError('body in json message must be base64')

        verb = json.get('verb')
        if verb is None or len(verb.strip()) == 0:
            raise RuntimeError('verb may not be blank')

        room_name_b64 = json.get('room_name')
        room_id = None

        # choose room by name
        if room_name_b64:
            try:
                room_name = utils.b64d(room_name_b64)
            except Exception as e:
                logger.error('could not decode room_name as base64: {}'.format(str(e)))
                raise RuntimeError('room name is not base64')

            try:
                room_id = utils.get_room_id(room_name, use_default_channel=True)
            except NoSuchRoomException:
                logger.error('no such room for name "{}"'.format(room_name))
                raise RuntimeError('no room found for name')

            logger.debug("broadcasting to room id {} ({})".format(room_id, room_name))

        data = utils.activity_for_broadcast(body, verb, room_id, room_name_b64)

        # if 'room_to_broadcast_to' is None, the event will be broadcasted to all connected users
        environ.env.out_of_scope_emit(
            'gn_broadcast', data, room=room_id,
            json=True, namespace='/ws', broadcast=True
        )
