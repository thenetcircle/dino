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

from datetime import datetime
from flask import request
from functools import lru_cache

from dino.rest.resources.base import BaseResource
from dino.admin.orm import storage_manager
from dino.utils import b64e
from dino.utils.decorators import timeit

logger = logging.getLogger(__name__)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class HistoryResource(BaseResource):
    def __init__(self):
        super(HistoryResource, self).__init__()
        self.last_cleared = datetime.utcnow()
        self.request = request

    def _get_lru_method(self):
        return self.do_get_with_params

    def _get_last_cleared(self):
        return self.last_cleared

    def _set_last_cleared(self, last_cleared):
        self.last_cleared = last_cleared

    @lru_cache()
    def do_get_with_params(self, room_id, user_id, from_time, to_time):
        return storage_manager.find_history(room_id, user_id, from_time, to_time)

    @timeit(logger, 'on_rest_history')
    def do_get(self):
        the_json = self.validate_json()
        logger.debug('GET request: %s' % str(the_json))

        room_id = the_json.get('room_id')
        user_id = the_json.get('user_id')
        from_time = the_json.get('from_time')
        to_time = the_json.get('to_time')

        try:
            messages = self.do_get_with_params(room_id, user_id, from_time, to_time)
            for message in messages:
                message['from_user_name'] = b64e(message['from_user_name'])
                message['body'] = b64e(message['body'])
                message['target_name'] = b64e(message['target_name'])
                message['channel_name'] = b64e(message['channel_name'])
            return messages
        except Exception as e:
            logger.error('could not get messages: %s' % str(e))
            raise e

    def validate_json(self):
        try:
            the_json = self.request.get_json(silent=True)
        except Exception as e:
            logger.error('error: %s' % str(e))
            logger.exception(traceback.format_exc())
            raise ValueError('invalid json')

        if the_json is None:
            logger.error('empty request body')
            raise ValueError('empty request body')

        return the_json
