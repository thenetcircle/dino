import logging
from datetime import datetime

from activitystreams import parse as parse_to_as
from flask import request

from dino import utils
from dino.rest.resources.base import BaseResource
from dino.utils.decorators import timeit

logger = logging.getLogger(__name__)


class UsersInRoomsResource(BaseResource):
    def __init__(self):
        super(UsersInRoomsResource, self).__init__()
        self.last_cleared = datetime.utcnow()
        self.request = request

    def _do_get(self, room_id: str = None, room_name: str = None):
        output = list()
        list_activity = parse_to_as({
            "verb": "list",
            "target": {
                "id": room_id
            }
        })

        if room_id is not None:
            users = utils.get_users_in_room(room_id=room_id, skip_cache=False)
        else:
            users = utils.get_users_in_room(room_name=room_name, skip_cache=False)

        activity = utils.activity_for_users_in_room(list_activity, users)

        for user in activity["object"]["attachments"]:
            output.append({
                'id': user["id"],
                'name': user["displayName"],
                'info': {
                    attachment["objectType"]: attachment["content"]
                    for attachment in user["attachments"]
                },
                'roles': user["content"]
            })

        return output

    def do_get_with_params(self, room_id: str = None, room_name: str = None):
        return self._do_get(room_id, room_name)

    @timeit(logger, 'on_rest_rooms_for_users')
    def do_get(self):
        is_valid, msg, json = self.validate_json(self.request, silent=False)
        if not is_valid:
            logger.error('invalid json: %s' % msg)
            return dict()

        logger.debug('GET request: %s' % str(json))
        if 'room_ids' not in json and 'room_names' not in json:
            return dict()

        output = dict()

        if 'room_ids' in json:
            for room_id in json['room_ids']:
                output[room_id] = self.do_get_with_params(room_id=room_id)

        if 'room_names' in json:
            for room_name in json['room_names']:
                output[room_name] = self.do_get_with_params(room_name=room_name)

        return output

    def _get_lru_method(self):
        return self.do_get_with_params

    def _get_last_cleared(self):
        return self.last_cleared

    def _set_last_cleared(self, last_cleared):
        self.last_cleared = last_cleared
