import activitystreams

import logging
import traceback
import sys

from dino import environ
from dino import utils
from dino.utils.decorators import timeit
from dino.db.manager import UserManager
from dino.rest.resources.base import BaseResource
from dino.exceptions import NoSuchUserException

from flask import request
from eventlet.greenpool import GreenPool

logger = logging.getLogger(__name__)


def fail(error_message):
    return {
        'status': 'FAIL',
        'message': error_message
    }


def ok():
    return {
        'status': 'OK'
    }


class HeartbeatResource(BaseResource):
    def __init__(self):
        super(HeartbeatResource, self).__init__()
        self.user_manager = UserManager(environ.env)
        self.executor = GreenPool()
        self.request = request
        self.env = environ.env

    def do_post(self):
        try:
            json = self._validate_params()
            self._do_post(json)
            return ok()
        except Exception as e:
            logger.error('could not heartbeat user: %s' % str(e))
            logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            return fail(str(e))

    def _validate_params(self):
        is_valid, msg, json = self.validate_json(self.request, silent=False)
        if not is_valid:
            raise RuntimeError('invalid json: %s' % msg)

        if json is None:
            raise RuntimeError('no json in request')
        if not isinstance(json, list):
            raise RuntimeError('need a dict of user-room keys')

        return json

    @timeit(logger, 'on_rest_auth')
    def _do_post(self, json: dict):
        logger.debug('POST request: %s' % str(json))
        for user_id in json:
            try:
                self.heartbeat_user(user_id)
            except Exception as e:
                self.env.capture_exception(sys.exc_info())
                logger.error('could not auth user %s: %s' % (user_id, str(e)))

    def heartbeat_user(self, user_id: str):
        try:
            user_name = utils.get_user_name_for(user_id)
        except NoSuchUserException:
            user_name = str(user_id)

        try:
            data = {
                'actor': {
                    'id': user_id,
                    'displayName': user_name
                },
                'verb': 'heartbeat'
            }

            environ.env.heartbeat.add_heartbeat(user_id)
            environ.env.observer.emit('on_heartbeat', (data, activitystreams.parse(data)))
        except ValueError as e:
            logger.error('invalid auth for user %s: %s' % (user_id, str(e)))
            self.env.capture_exception(sys.exc_info())
        except NoSuchUserException as e:
            logger.error('no such user %s: %s' % (user_id, str(e)))
            self.env.capture_exception(sys.exc_info())
        except Exception as e:
            logger.error('could not auth user %s: %s' % (user_id, str(e)))
            logger.error(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
