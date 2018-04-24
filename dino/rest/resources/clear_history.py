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
import time

from dino import environ
from dino.utils.decorators import timeit
from dino.db.manager import StorageManager
from dino.rest.resources.base import BaseResource

from flask import request

logger = logging.getLogger(__name__)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class ClearHistoryResource(BaseResource):
    def __init__(self):
        super(ClearHistoryResource, self).__init__()
        self.storage_manager = StorageManager(environ.env)
        self.request = request

    @timeit(logger, 'on_rest_clear_history')
    def do_post(self):
        is_valid, msg, json = self.validate_json()
        if not is_valid:
            logger.error('invalid json: %s' % msg)
            raise RuntimeError('invalid json')

        if json is None:
            raise RuntimeError('no json in request')
        if not isinstance(json, dict):
            raise RuntimeError('need a dict of user-room keys')
        logger.debug('POST request: %s' % str(json))

        if 'id' not in json:
            raise RuntimeError('no id parameter in request')

        user_id = json.get('id')
        before = time.time()
        messages = self.storage_manager.get_all_message_from_user(user_id)
        logger.info('about to delete %s messages for user %s (fetching IDs took %.2fs)' % (len(messages), user_id, time.time()-before))

        before = time.time()
        failures = 0
        successes = 0

        for message_id in messages:
            try:
                self.storage_manager.delete_message(message_id)
                successes += 1
            except Exception as e:
                logger.error('could not delete message with id %s because: %s' % (message_id, str(e)))
                logger.exception(traceback.format_exc())
                failures += 1

        logger.info('finished deleting %s message for user %s (deletion took %.2fs)' % (len(messages), user_id, time.time()-before))

        return {'status': 'OK', 'failed': failures, 'success': successes, 'total': failures+successes}

    def validate_json(self):
        try:
            return True, None, self.request.get_json(silent=False)
        except Exception as e:
            logger.error('error: %s' % str(e))
            logger.exception(traceback.format_exc())
            return False, 'invalid json in request', None
