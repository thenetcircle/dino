import logging
import traceback
import sys

from dino import environ
from dino.utils.decorators import timeit
from dino.db.manager import UserManager
from dino.rest.resources.base import BaseResource
from dino.exceptions import NoSuchUserException

from flask import request
from eventlet.greenpool import GreenPool

logger = logging.getLogger(__name__)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


def fail(error_message):
    return {
        'status': 'FAIL',
        'message': error_message
    }


def ok():
    return {
        'status': 'OK'
    }


class AuthenticateResource(BaseResource):
    def __init__(self):
        super(AuthenticateResource, self).__init__()
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
            logger.error('could not authenticate user: %s' % str(e))
            logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            return fail(str(e))

    def _validate_params(self):
        is_valid, msg, json = self.validate_json(self.request, silent=False)
        if not is_valid:
            raise RuntimeError('invalid json: %s' % msg)

        if json is None:
            raise RuntimeError('no json in request')
        if not isinstance(json, dict):
            raise RuntimeError('need a dict of user-room keys')

        for user_id, auth_info in json.items():
            # todo: some required info to authenticate?
            pass

        return json

    @timeit(logger, 'on_rest_auth')
    def _do_post(self, json: dict):
        logger.debug('POST request: %s' % str(json))
        for user_id, auth_info in json.items():
            try:
                self.auth_user(user_id, auth_info)
            except Exception as e:
                self.env.capture_exception(sys.exc_info())
                logger.error('could not auth user %s: %s' % (user_id, str(e)))

    def auth_user(self, user_id: str, auth_info: dict):
        try:
            self.user_manager.auth_user(user_id, auth_info)
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
