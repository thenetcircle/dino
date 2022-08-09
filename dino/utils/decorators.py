import traceback
import logging
import time
import sys
import activitystreams as as_parser
import eventlet

from functools import wraps
from datetime import datetime
from uuid import uuid4 as uuid

from dino import validation
from dino import environ
from dino import utils
from dino.exceptions import NoSuchUserException
from dino.config import ConfigKeys
from dino.config import SessionKeys
from dino.config import ErrorCodes

logger = logging.getLogger(__name__)
emit_responses = environ.env.config.get(ConfigKeys.EMIT_RESPONSES, default=True)


def timeit(_logger, tag: str):
    def factory(view_func):
        @wraps(view_func)
        def decorator(*args, **kwargs):
            failed = False
            before = time.time()
            try:
                return view_func(*args, **kwargs)
            except Exception as e:
                failed = True
                _logger.exception(traceback.format_exc())
                _logger.error(tag + '... FAILED')
                environ.env.capture_exception(sys.exc_info())
                raise e
            finally:
                if not failed:
                    the_time = (time.time()-before)*1000
                    if tag.startswith('on_') and environ.env.stats is not None:
                        environ.env.stats.timing('api.' + tag, the_time)
                    else:
                        _logger.debug(tag + '... %.2fms' % the_time)
        return decorator
    return factory


def locked_method(method):
    """Method decorator. Requires a lock object at self._lock"""
    def newmethod(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return newmethod


def _delayed_disconnect(sid: str):
    environ.env.disconnect_by_sid(sid)


def respond_with(gn_event_name=None, should_disconnect=False, use_callback=True):
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
                environ.env.capture_exception(sys.exc_info())

                if should_disconnect and environ.env.config.get(ConfigKeys.DISCONNECT_ON_FAILED_LOGIN, False):
                    eventlet.spawn_after(seconds=1, func=_delayed_disconnect, sid=environ.env.request.sid)
                return 500, str(e)
            finally:
                if tb is not None:
                    logger.exception(tb)

            if status_code != 200:
                logger.warning('in decorator, status_code: %s, data: %s' % (status_code, str(data)))
                if should_disconnect and environ.env.config.get(ConfigKeys.DISCONNECT_ON_FAILED_LOGIN, False):
                    eventlet.spawn_after(seconds=1, func=_delayed_disconnect, sid=environ.env.request.sid)

            response_message = environ.env.response_formatter(status_code, data)

            # avoid breaking old app versions by still emitting events
            if emit_responses:
                environ.env.emit(gn_event_name, response_message)

            return response_message
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
                    logger.warning('unknown connect type "%s"' % connect_type)
            except Exception as e:
                logger.error('could not record statistics: %s' % str(e))
                environ.env.capture_exception(sys.exc_info())

            return view_func(*args, **kwargs)
        return decorator
    return factory


def can_use_room_name():
    def factory(view_func):
        @wraps(view_func)
        def decorator(*args, **kwargs):
            def add_target_id_if_missing(data):
                if 'target' not in data or 'objectType' not in data['target']:
                    return data

                if data['target']['objectType'] == 'name':
                    room_id = utils.get_room_id(data['target']['id'], use_default_channel=True)
                    data['target']['id'] = room_id

                return data

            try:
                data = args[0]
                data = add_target_id_if_missing(data)
                return view_func(*(data, *args[1:]), **kwargs)
            except Exception as e:
                logger.error(str(e))
                environ.env.capture_exception(sys.exc_info())
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
                            except NoSuchUserException:
                                error_msg = '[%s] no user found for user_id "%s" in session' % \
                                            (validation_name, str(data['actor']['id']))
                                logger.error(error_msg)
                                return ErrorCodes.NO_USER_IN_SESSION, error_msg
                        data['actor']['displayName'] = utils.b64e(user_name)

                    activity = as_parser.parse(data)

                    # the login request will not have user id in session yet, which this would check
                    if should_validate_request:
                        is_valid, error_msg = validation.request.validate_request(activity)
                        if not is_valid:
                            logger.error('[%s] validation failed, error message: %s' % (validation_name, str(error_msg)))
                            return ErrorCodes.VALIDATION_ERROR, error_msg

                    is_valid, status_code, message = getattr(validation.request, validation_name)(activity)
                    if is_valid:
                        all_ok = True
                        if validation_name in environ.env.event_validator_map:
                            for validator in environ.env.event_validator_map[validation_name]:
                                all_ok, status_code, msg = validator(data, activity)
                                if not all_ok:
                                    logger.warning(
                                            '[%s] validator "%s" failed: %s' %
                                            (validation_name, str(validator), str(msg)))
                                    break

                        if all_ok:
                            args = (data, activity)
                            status_code, message = view_func(*args, **kwargs)

                except Exception as e:
                    logger.error('%s: %s' % (validation_name, str(e)))
                    logger.exception(traceback.format_exc())
                    environ.env.stats.incr('event.' + validation_name + '.exception')
                    environ.env.capture_exception(sys.exc_info())
                    return ErrorCodes.UNKNOWN_ERROR, str(e)

                if status_code == 200:
                    environ.env.stats.incr('event.' + validation_name + '.count')
                else:
                    environ.env.stats.incr('event.' + validation_name + '.error')
                    logger.warning('in decorator for %s, status_code: %s, message: %s' %
                                (validation_name, status_code, str(message)))
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
