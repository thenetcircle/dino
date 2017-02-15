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
from dino import utils
from dino.exceptions import NoSuchUserException
from dino.config import ConfigKeys
from dino.config import SessionKeys

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger()


def respond_with(gn_event_name=None):
    def factory(view_func):
        @wraps(view_func)
        def decorator(*args, **kwargs):
            tb = None
            try:
                status_code, data = view_func(*args, **kwargs)
            except Exception as e:
                environ.env.stats.incr(gn_event_name + '.exception')
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


def pre_process(validation_name, should_validate_request=True):
    def factory(view_func):
        @wraps(view_func)
        def decorator(*a, **k):
            def _pre_process(*args, **kwargs):
                if not hasattr(validation.request, validation_name):
                    raise RuntimeError('no such attribute on validation.request: %s' % validation_name)

                try:
                    data = args[0]
                    if 'actor' not in data:
                        data['actor'] = dict()

                    # let the server determine the publishing time of the event, not the client
                    # use default time format, since activity streams only accept RFC3339 format
                    data['published'] = datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
                    data['id'] = str(uuid())

                    if should_validate_request:
                        data['actor']['id'] = str(environ.env.session.get(SessionKeys.user_id.value))
                        user_name = environ.env.session.get(SessionKeys.user_name.value)
                        if user_name is None or len(user_name.strip()) == 0:
                            try:
                                user_name = utils.get_user_name_for(data['actor']['id'])
                            except NoSuchUserException as e:
                                return 400, str(e)
                        data['actor']['displayName'] = utils.b64e(user_name)

                    activity = as_parser.parse(data)

                    # the login request will not have user id in session yet, which this would check
                    if should_validate_request:
                        is_valid, error_msg = validation.request.validate_request(activity)
                        if not is_valid:
                            return 400, error_msg

                    is_valid, status_code, message = getattr(validation.request, validation_name)(activity)
                    if is_valid:
                        all_ok = True
                        if validation_name in environ.env.event_validator_map:
                            for validator in environ.env.event_validator_map[validation_name]:
                                all_ok, msg = validator(data, activity)
                                if not all_ok:
                                    logger.warn(
                                            'validator "%s" failed for event "%s": %s' %
                                            (str(validator), validation_name, msg))
                                    status_code, message = 400, msg
                                    break

                        if all_ok:
                            args = (data, activity)
                            status_code, message = view_func(*args, **kwargs)

                except Exception as e:
                    logger.error('%s: %s' % (validation_name, str(e)))
                    logger.exception(traceback.format_exc())
                    environ.env.stats.incr('event.' + validation_name + '.exception')
                    return 500, str(e)

                if status_code == 200:
                    environ.env.stats.incr('event.' + validation_name + '.count')
                else:
                    environ.env.stats.incr('event.' + validation_name + '.error')
                    logger.warn('in decorator, status_code: %s, message: %s' % (status_code, str(message)))
                return status_code, message

            start = time.time()
            exception_occurred = False
            try:
                environ.env.stats.incr('event.' + validation_name + '.count')
                return _pre_process(*a, **k)
            except:
                exception_occurred = True
                environ.env.stats.incr('event.' + validation_name + '.exception')
                raise
            finally:
                if not exception_occurred:
                    environ.env.stats.timing('event.' + validation_name, (time.time()-start)*1000)
        return decorator
    return factory
