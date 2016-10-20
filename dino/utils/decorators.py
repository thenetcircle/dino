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

import traceback
import logging
import activitystreams as as_parser

from functools import wraps
from datetime import datetime
from uuid import uuid4 as uuid

from dino import validation
from dino.config import ConfigKeys

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


def pre_process(validation_name=None, should_validate_request=True):
    def factory(view_func):
        @wraps(view_func)
        def decorator(*args, **kwargs):
            tb = None

            if not hasattr(validation.request, validation_name):
                raise RuntimeError('no such attribute on validation.request: %s' % validation_name)

            try:
                data = args[0]

                # let the server determine the publishing time of the event, not the client
                # use default time format, since activity streams only accept RFC3339 format
                data['published'] = datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
                data['id'] = str(uuid())
                activity = as_parser.parse(data)

                # the login request will not have user id in session yet, which this would check
                if should_validate_request:
                    is_valid, error_msg = validation.request.validate_request(activity)
                    if not is_valid:
                        return 400, error_msg

                is_valid, status_code, message = getattr(validation.request, validation_name)(activity)
                if is_valid:
                    args = (data, activity)
                    status_code, message = view_func(*args, **kwargs)

            except Exception as e:
                logger.error('%s: %s' % (validation_name, str(e)))
                print(traceback.format_exc())
                return 500, str(e)

            if status_code != 200:
                logger.warn('in decorator, status_code: %s, message: %s' % (status_code, str(message)))
            return status_code, message
        return decorator
    return factory
