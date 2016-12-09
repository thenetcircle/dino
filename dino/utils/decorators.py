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
import time
import activitystreams as as_parser

from functools import wraps
from datetime import datetime
from uuid import uuid4 as uuid

from dino import validation
from dino import environ
from dino.config import ConfigKeys
from dino.config import SessionKeys

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


def respond_with(gn_event_name=None):
    def factory(view_func):
        @wraps(view_func)
        def decorator(*args, **kwargs):
            tb = None
            try:
                status_code, data = view_func(*args, **kwargs)
            except Exception as e:
                tb = traceback.format_exc()
                logger.error('%s: %s' % (gn_event_name, str(e)))
                return 500, str(e)
            finally:
                if tb is not None:
                    logger.exception(tb)

            if status_code != 200:
                logger.warn('in decorator, status_code: %s, data: %s' % (status_code, str(data)))
            if data is not None:
                environ.env.emit(gn_event_name, {'status_code': status_code, 'data': data})
            else:
                environ.env.emit(gn_event_name, {'status_code': status_code})
            return status_code, None
        return decorator
    return factory


def count_connections(connect_type=None):
    def factory(view_func):
        @wraps(view_func)
        def decorator(*args, **kwargs):
            try:
                if connect_type == 'connect':
                    environ.env.stats.incr('connections')
                elif connect_type == 'disconnect':
                    environ.env.stats.decr('connections')
                else:
                    logger.warn('unknown connect type "%s"' % connect_type)
            except Exception as e:
                logger.error('could not record statistics: %s' % str(e))

            return view_func(*args, **kwargs)
        return decorator
    return factory


def pre_process(validation_name=None, should_validate_request=True):
    def factory(view_func):
        @wraps(view_func)
        def decorator(*args, **kwargs):
            if not hasattr(validation.request, validation_name):
                raise RuntimeError('no such attribute on validation.request: %s' % validation_name)

            before = time.time()
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
                logger.exception(traceback.format_exc())
                environ.env.stats.incr(validation_name + '.exception')
                return 500, str(e)

            finally:
                exec_time_ms = (time.time()-before)*1000
                environ.env.stats.timing(validation_name, exec_time_ms)

            if status_code == 200:
                environ.env.stats.incr(validation_name)
            else:
                environ.env.stats.incr(validation_name + '.error')
                logger.warn('in decorator, status_code: %s, message: %s' % (status_code, str(message)))
            return status_code, message
        return decorator
    return factory
