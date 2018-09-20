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

from dino import environ
from dino import utils
from dino.utils.decorators import timeit
from dino.db.manager import UserManager
from dino.rest.resources.base import BaseResource

from flask import request

logger = logging.getLogger(__name__)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


def fail(error_message):
    return {
        'status': 'FAIL',
        'message': error_message
    }


class SendResource(BaseResource):
    def __init__(self):
        super(SendResource, self).__init__()
        self.user_manager = UserManager(environ.env)
        self.request = request

    @timeit(logger, 'on_rest_send')
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

        if 'content' not in json:
            raise RuntimeError('no key [content] in json message')

        msg_content = json.get('content')
        if msg_content is None or len(msg_content.strip()) == 0:
            raise RuntimeError('content may not be blank')
        if not utils.is_base64(msg_content):
            raise RuntimeError('content in json message must be base64')

        user_id = json.get('user_id', 0)
        user_name = utils.b64d(json.get('user_name', 'admin'))
        object_type = json.get('object_type')
        target_id = json.get('target_id')
        target_name = json.get('target_name')

        data = utils.activity_for_message(user_id, user_name)
        data['target'] = {
            'objectType': object_type,
            'id': str(target_id),
            'displayName': target_name
        }
        data['object'] = {
            'content': msg_content
        }

        environ.env.internal_publisher.publish(data)
