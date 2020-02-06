import logging
import traceback

from datetime import datetime
from flask import request
from functools import lru_cache

from dino.rest.resources.base import BaseResource
from dino.admin.orm import storage_manager
from dino.utils import b64e
from dino.utils.decorators import timeit

logger = logging.getLogger(__name__)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class LatestHistoryResource(BaseResource):
    def __init__(self):
        super().__init__(cache_clear_interval=30)
        self.last_cleared = datetime.utcnow()
        self.request = request

    def _get_lru_method(self):
        return self.do_get_with_params

    def _get_last_cleared(self):
        return self.last_cleared

    def _set_last_cleared(self, last_cleared):
        self.last_cleared = last_cleared

    @lru_cache()
    def do_get_with_params(self, room_id, limit):
        return storage_manager.get_latest_messages(room_id, limit)

    @timeit(logger, 'on_rest_latest_history')
    def do_get(self):
        the_json = self.validate_json()
        logger.debug('GET request: %s' % str(the_json))

        room_id = the_json.get('room_id', '')
        limit = the_json.get('limit', 100)

        try:
            messages = self.do_get_with_params(room_id, limit)
            for message in messages:
                message['from_user_name'] = b64e(message['from_user_name'])
                message['body'] = b64e(message['body'])
                message['target_name'] = b64e(message['target_name'])
                message['channel_name'] = b64e(message['channel_name'])
            return messages
        except Exception as e:
            logger.error('could not get messages: %s' % str(e))
            raise e

    def validate_json(self):
        try:
            the_json = self.request.get_json(silent=True)
        except Exception as e:
            logger.error('error: %s' % str(e))
            logger.exception(traceback.format_exc())
            raise ValueError('invalid json')

        if the_json is None:
            logger.error('empty request body')
            raise ValueError('empty request body')

        return the_json
