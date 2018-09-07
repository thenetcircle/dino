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

from datetime import datetime
from flask import request

import logging
import traceback

from dino.rest.resources.base import BaseResource
from dino.utils.decorators import timeit
from dino import environ

logger = logging.getLogger(__name__)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class RolesResource(BaseResource):
    def __init__(self):
        super(RolesResource, self).__init__()
        self.last_cleared = datetime.utcnow()
        self.request = request

    def _get_lru_method(self):
        return self.do_get_with_params

    def _get_last_cleared(self):
        return self.last_cleared

    def _set_last_cleared(self, last_cleared):
        self.last_cleared = last_cleared

    def do_get_with_params(self, user_id):
        return environ.env.db.get_user_roles(user_id)

    @timeit(logger, 'on_rest_roles')
    def do_get(self):
        is_valid, msg, json = self.validate_json()
        if not is_valid:
            logger.error('invalid json: %s' % msg)
            return dict()

        if json is None:
            return environ.env.db.get_banned_users()

        if 'users' not in json:
            return dict()
        logger.debug('GET request: %s' % str(json))

        output = dict()
        for user_id in json['users']:
            output[user_id] = self.do_get_with_params(user_id)
        return output

    def validate_json(self):
        try:
            return True, None, self.request.get_json(silent=True)
        except Exception as e:
            logger.error('error: %s' % str(e))
            logger.exception(traceback.format_exc())
            return False, 'invalid json in request', None
