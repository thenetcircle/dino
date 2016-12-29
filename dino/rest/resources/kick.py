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
from dino.db.manager import UserManager
from dino.rest.resources.base import BaseResource

from flask import request

logger = logging.getLogger(__name__)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class KickResource(BaseResource):
    def __init__(self):
        super(KickResource, self).__init__()
        self.user_manager = UserManager(environ.env)
        self.request = request

    def do_post(self):
        is_valid, msg, json = self.validate_json()
        output = dict()
        if not is_valid:
            logger.error('invalid json: %s' % msg)
            return output

        if json is None:
            raise RuntimeError('no json in request')
        if not isinstance(json, dict):
            raise RuntimeError('need a dict of user-room keys')
        logger.debug('POST request: %s' % str(json))

        for user_id, kick_info in json.items():
            try:
                reason = kick_info.get('reason')
                admin_id = kick_info.get('admin_id')
                room_id = kick_info.get('target')

                self.user_manager.kick_user(room_id, user_id, reason, admin_id)
                output[user_id] = 'OK'
            except Exception:
                logger.error('no such room when trying to kick user %s for %s' % (user_id, kick_info))
                logger.error(traceback.format_exc())
                output[user_id] = 'FAIL'
                continue
        return output

    def validate_json(self):
        try:
            return True, None, self.request.get_json(silent=False)
        except Exception as e:
            logger.error('error: %s' % str(e))
            logger.exception(traceback.format_exc())
            return False, 'invalid json in request', None
