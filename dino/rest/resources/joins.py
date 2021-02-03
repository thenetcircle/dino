import logging
from datetime import datetime

from flask import request

from dino import environ
from dino.exceptions import NoSuchRoomException
from dino.rest.resources.base import BaseResource
from dino.utils.decorators import timeit

logger = logging.getLogger(__name__)


class JoinsInRoomResource(BaseResource):
    def __init__(self):
        super(JoinsInRoomResource, self).__init__()
        self.last_cleared = datetime.utcnow()
        self.request = request

    def _do_get(self, room_id):
        try:
            return environ.env.db.get_joins_in_room(room_id) or 0
        except NoSuchRoomException:
            e_msg = "no such room: {}".format(room_id)
            logger.error(e_msg)
            raise RuntimeError(e_msg)
        except Exception as e:
            e_msg = "no such room: {}".format(room_id)
            logger.error(e_msg)
            logger.exception(e)
            raise RuntimeError(str(e))

    def do_get_with_params(self, user_id):
        return self._do_get(user_id)

    @timeit(logger, 'on_rest_rooms_for_users')
    def do_get(self):
        is_valid, msg, json = self.validate_json(self.request, silent=False)
        if not is_valid:
            logger.error('invalid json: %s' % msg)
            return dict()

        logger.debug('GET request: %s' % str(json))
        if 'room_ids' not in json:
            return dict()

        output = dict()
        for room_id in json['room_ids']:
            output[room_id] = self.do_get_with_params(room_id)

        return output

    def _get_lru_method(self):
        return self.do_get_with_params

    def _get_last_cleared(self):
        return self.last_cleared

    def _set_last_cleared(self, last_cleared):
        self.last_cleared = last_cleared
