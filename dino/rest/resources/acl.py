import logging
import sys
import traceback
from datetime import datetime

from eventlet.greenpool import GreenPool
from flask import request

from dino import environ
from dino.db.manager.acls import AclManager
from dino.rest.resources.base import BaseResource

logger = logging.getLogger(__name__)


def fail(error_message):
    return {
        'status': 'FAIL',
        'message': error_message
    }


def ok(data: dict = None):
    output = {'status': 'OK'}
    if data is not None:
        output['data'] = data
    return output


class AclResource(BaseResource):
    def __init__(self):
        super(AclResource, self).__init__()
        self.acl_manager = AclManager(environ.env)
        self.last_cleared = datetime.utcnow()
        self.executor = GreenPool()
        self.request = request
        self.env = environ.env

    def do_post(self):
        try:
            json_data = self._validate_params()
            self._do_post(json_data)
            return ok()
        except Exception as e:
            logger.error('could not ban user: %s' % str(e))
            logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            return fail(str(e))

    def do_get(self):
        try:
            data = self._do_get()
            return ok(data)
        except Exception as e:
            logger.error('could not get rooms with acls: {}'.format(str(e)))
            logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            return fail(str(e))

    def _do_post(self, json_data: dict):
        logger.debug('POST request: %s' % str(json_data))

        room_id = json_data.get('room_id')
        action = json_data.get('action')
        acl_type = json_data.get('acl_type')
        acl_value = json_data.get('acl_value')

        try:
            channel_id = self.env.db.channel_for_room(room_id)
            self.acl_manager.update_room_acl(channel_id, room_id, action, acl_type, acl_value)
        except Exception as e:
            logger.error('could update acls in room {} with action={}, type={}, value="{}": {}'.format(
                room_id, action, acl_type, acl_value, str(e))
            )
            logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())

    def _do_get(self):
        room_ids = self.env.db.get_all_permanent_rooms()
        output = dict()

        for room_id in room_ids:
            acls = self.acl_manager.get_acls_room(room_id, encode_result=False)
            output[room_id] = acls

        return output

    def _validate_params(self):
        is_valid, msg, json_data = self.validate_json(self.request, silent=False)
        if not is_valid:
            raise RuntimeError('invalid json: %s' % msg)

        if json_data is None:
            raise RuntimeError('no json in request')
        if not isinstance(json_data, dict):
            raise RuntimeError('need a dict')

        if 'room_id' not in json_data:
            raise KeyError('missing parameter room_id for in request')
        if 'action' not in json_data:
            raise KeyError('missing parameter action for in request')
        if 'acl_type' not in json_data:
            raise KeyError('missing parameter acl_type for in request')
        if 'acl_value' not in json_data:
            raise KeyError('missing parameter acl_value for in request')

    def _get_lru_method(self):
        return self.do_get_with_params

    def _get_last_cleared(self):
        return self.last_cleared

    def _set_last_cleared(self, last_cleared):
        self.last_cleared = last_cleared
