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

from activitystreams import parse
from dino.utils.activity_helper import ActivityBuilder

from dino import environ
from dino.utils.decorators import timeit
from dino.exceptions import UserExistsException
from dino.rest.resources.base import BaseResource

from flask import request

logger = logging.getLogger(__name__)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class SetStatusResource(BaseResource):
    def __init__(self):
        super(SetStatusResource, self).__init__()
        self.request = request

    @timeit(logger, 'on_rest_status')
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
        if 'status' not in json:
            raise RuntimeError('no status parameter in request')

        user_id = json.get('id')
        status = json.get('status')
        stage = json.get('stage', 'status')

        all_statuses = {'online', 'offline', 'invisible', 'visible'}
        if status not in all_statuses:
            raise RuntimeError('unknown status [{}], need one of [{}]'.format(status, ','.join(all_statuses)))

        all_stages = {'status', 'login'}
        if stage not in all_stages:
            raise RuntimeError('unknown stage [{}], need one of [{}]'.format(stage, ','.join(all_stages)))

        try:
            environ.env.db.create_user(user_id, str(user_id))
        except UserExistsException:
            pass

        activity_base = {
            'actor': {
                'id': user_id,
                'summary': stage
            },
            'verb': status
        }
        data = ActivityBuilder.enrich(activity_base)
        activity = parse(data)
        environ.env.observer.emit('on_status', (data, activity))

    def validate_json(self):
        try:
            return True, None, self.request.get_json(silent=False)
        except Exception as e:
            logger.error('error: %s' % str(e))
            logger.exception(traceback.format_exc())
            return False, 'invalid json in request', None
