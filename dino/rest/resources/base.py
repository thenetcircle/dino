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

from datetime import datetime
from flask_restful import Resource

import logging
import traceback

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class BaseResource(Resource):
    CACHE_CLEAR_INTERVAL = 20  # 20 seconds

    def get(self):
        if (datetime.utcnow() - self._get_last_cleared()).total_seconds() > BaseResource.CACHE_CLEAR_INTERVAL:
            self._get_lru_method().cache_clear()
            self._set_last_cleared(datetime.utcnow())

        try:
            return {'status_code': 200, 'data': self.do_get()}
        except Exception as e:
            logging.error('could not do get: %s' % str(e))
            logging.exception(traceback.format_exc())
            return {'status_code': 500, 'data': str(e)}

    def do_get(self):
        raise NotImplementedError()

    def _get_lru_method(self):
        raise NotImplementedError()

    def _get_last_cleared(self):
        raise NotImplementedError()

    def _set_last_cleared(self, last_cleared):
        raise NotImplementedError()
