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
import traceback


from dino import environ
from dino.exceptions import UserExistsException
from dino.rest.resources.base import BaseResource

from flask import request

logger = logging.getLogger(__name__)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class SetAdminResource(BaseResource):
    def __init__(self):
        super(SetAdminResource, self).__init__()
        self.request = request

    def do_post(self):
        is_valid, msg, json = self.validate_json()
        if not is_valid:
            logger.error('invalid json: %s' % msg)
            raise RuntimeError('invalid json')

        if json is None:
            raise RuntimeError('no json in request')
        if not isinstance(json, dict):
            raise RuntimeError('need a dict')
        logger.debug('POST request: %s' % str(json))

        if 'id' not in json:
            raise RuntimeError('no id parameter in request')
        if 'name' not in json:
            raise RuntimeError('no name parameter in request')

        user_id = json.get('id')
        user_name = json.get('name')

        try:
            environ.env.db.create_user(user_id, user_name)
        except UserExistsException:
            pass

        try:
            environ.env.db.set_global_moderator(user_id)
        except Exception as e:
            logger.error('could not set user with id "%s" as global moderator: %s' % (str(user_id), str(e)))
            logger.exception(traceback.format_exc())
            raise RuntimeError('could not set user with id "%s" as global moderator: %s' % (str(user_id), str(e)))

    def validate_json(self):
        try:
            return True, None, self.request.get_json(silent=False)
        except Exception as e:
            logger.error('error: %s' % str(e))
            logger.exception(traceback.format_exc())
            return False, 'invalid json in request', None
