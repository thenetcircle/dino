
import logging
import traceback

from dino import environ
from dino.utils.decorators import timeit
from dino.db.manager import UserManager
from dino.rest.resources.base import BaseResource

from dino import utils
from flask import request

logger = logging.getLogger(__name__)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class KickResource(BaseResource):
    def __init__(self):
        super(KickResource, self).__init__()
        self.user_manager = UserManager(environ.env)
        self.request = request

    @timeit(logger, 'on_rest_kick')
    def do_post(self):
        is_valid, msg, json = self.validate_json()
        output = dict()

        if not is_valid:
            logger.error('invalid json: %s' % msg)
            return output

        if json is None:
            raise RuntimeError('no json in request')
        if not isinstance(json, dict):
            raise RuntimeError('need a dict of user-room keys')

        logger.debug('POST request: %s' % str(json))

        for user_id, kick_info in json.items():
            try:
                reason = kick_info.get('reason')
                admin_id = kick_info.get('admin_id')
                room_id, room_name = None, None

                if 'target' in kick_info:
                    room_id = kick_info.get('target')
                elif 'room_id' in kick_info:
                    room_id = kick_info.get('room_id')
                else:
                    room_name = kick_info.get('room_name')
                    room_name = utils.b64d(room_name)

                if room_id is not None and not len(room_id.strip()):
                    room_id = None
                if room_name is not None and not len(room_name.strip()):
                    room_name = None

                self.user_manager.kick_user(room_id, user_id, reason, admin_id, room_name=room_name)
                output[user_id] = 'OK'
            except Exception as e:
                logger.error('no such room when trying to kick user {} for {}: {}'.format(user_id, kick_info, str(e)))
                logger.error(traceback.format_exc())
                output[user_id] = 'FAIL'

        return output

    def validate_json(self):
        try:
            return True, None, self.request.get_json(silent=False)
        except Exception as e:
            logger.error('error: %s' % str(e))
            logger.exception(traceback.format_exc())
            return False, 'invalid json in request', None
