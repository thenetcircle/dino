import logging
import sys
import traceback

from flask import request

from dino import environ
from dino.db.manager import UserManager
from dino.rest.resources.base import BaseResource

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


class LogoutResource(BaseResource):
    def __init__(self):
        super(LogoutResource, self).__init__()
        self.user_manager = UserManager(environ.env)
        self.request = request
        self.env = environ.env

    def _validate_params(self):
        is_valid, msg, json = self.validate_json(self.request, silent=False)
        if not is_valid:
            raise RuntimeError('invalid json: %s' % msg)

        if json is None:
            raise RuntimeError('no json in request')
        if not isinstance(json, dict):
            raise RuntimeError('need a dict of user-room keys')

        if 'user_id' not in json:
            raise RuntimeError('no user_id in request')

        return json

    def do_post(self):
        try:
            json = self._validate_params()
            logger.debug('POST request: %s' % str(json))
            user_id = json['user_id']

            try:
                self.env.db.reset_sids_for_user(user_id)
            except Exception as e:
                logger.error('could not ban user %s: %s' % (user_id, str(e)))
                logger.exception(e)
                self.env.capture_exception(sys.exc_info())

            return ok()

        except Exception as e:
            logger.error('could not ban user: %s' % str(e))
            logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            return fail(str(e))
