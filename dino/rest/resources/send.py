import logging
import traceback
import eventlet

import sys

from dino import environ
from dino import utils
from dino.utils.decorators import timeit
from dino.db.manager import UserManager
from dino.rest.resources.base import BaseResource

from flask import request

logger = logging.getLogger(__name__)


def fail(error_message):
    return {
        'status': 'FAIL',
        'message': error_message
    }


class SendResource(BaseResource):
    def __init__(self):
        super(SendResource, self).__init__()
        self.user_manager = UserManager(environ.env)
        self.request = request

    def async_post(self, json):
        logger.debug('POST request: %s' % str(json))

        if 'content' not in json:
            raise RuntimeError('no key [content] in json message')

        msg_content = json.get('content')
        if msg_content is None or len(msg_content.strip()) == 0:
            raise RuntimeError('content may not be blank')
        if not utils.is_base64(msg_content):
            raise RuntimeError('content in json message must be base64')

        user_id = str(json.get('user_id', 0))
        user_name = utils.b64d(json.get('user_name', utils.b64e('admin')))
        object_type = json.get('object_type')
        target_id = json.get('target_id')
        namespace = json.get('namespace', '/ws')
        target_name = json.get('target_name')

        if target_id is None:
            if target_name is not None:
                decoded_target_name = utils.b64d(target_name)
                target_id = utils.get_room_id(decoded_target_name)
            else:
                raise RuntimeError("need either target_id or target_name to send messages, both are empty")

        data = utils.activity_for_message(user_id, user_name)
        data['target'] = {
            'objectType': object_type,
            'id': target_id,
            'displayName': target_name,
            'url': namespace
        }
        data['object'] = {
            'content': msg_content
        }

        if object_type == "private" and not environ.env.cache.user_is_in_multicast(target_id):
            logger.info('user {} is offline, dropping message: {}'.format(target_id, str(json)))
            return

        try:
            environ.env.out_of_scope_emit('message', data, room=target_id, json=True, namespace='/ws', broadcast=True)
        except Exception as e:
            logger.error('could not /send message to target {}: {}'.format(target_id, str(e)))
            logger.exception(traceback.format_exc())
            environ.env.capture_exception(sys.exc_info())

    @timeit(logger, 'on_rest_send')
    def do_post(self):
        is_valid, msg, json = self.validate_json(self.request, silent=False)
        if not is_valid:
            logger.error('invalid json: %s' % msg)
            raise RuntimeError('invalid json')

        if json is None:
            raise RuntimeError('no json in request')
        if not isinstance(json, dict):
            raise RuntimeError('need a dict')

        eventlet.spawn_n(self.async_post, dict(json))
