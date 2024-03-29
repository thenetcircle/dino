import logging
from datetime import datetime

from flask import request

from dino import environ
from dino import utils
from dino.config import ErrorCodes
from dino.exceptions import NoSuchUserException, NoSuchRoomException, UserIsBannedException
from dino.rest.resources.base import RoomNameBaseResource
from dino.utils.decorators import timeit

logger = logging.getLogger(__name__)


class JoinRoomResource(RoomNameBaseResource):
    def __init__(self):
        super(JoinRoomResource, self).__init__(environ.env)
        self.last_cleared = datetime.utcnow()
        self.request = request
        self.namespace = "/ws"

    def _do_post(self, room_id, room_name, user_ids):
        if room_id is None and room_name is not None:
            # try to join by room name instead of room id
            try:
                room_id = utils.get_room_id(room_name)
            except NoSuchRoomException:
                return {
                    "success": 0,
                    "failures": len(user_ids),
                    "errors": [{
                        "code": ErrorCodes.NO_SUCH_ROOM,
                        "message": "no room exists with id {} or name {}".format(room_id, room_name)
                    }]
                }

        errors = list()

        for user_id in user_ids:
            try:
                self.join(user_id, room_id, need_user_names=False)
            except UserIsBannedException as e:
                errors.append({
                    "code": ErrorCodes.USER_IS_BANNED,
                    "message": e.msg
                })
            except NoSuchUserException as e:
                errors.append({
                    "code": ErrorCodes.NO_SUCH_USER,
                    "message": "user not online: {}".format(e.uuid)
                })

        return {
            "success": len(user_ids) - len(errors),
            "failures": len(errors),
            "errors": errors
        }

    @timeit(logger, "on_rest_join_room")
    def do_post(self):
        is_valid, msg, json = self.validate_json(self.request, silent=False)
        if not is_valid:
            raise AttributeError(msg)

        logger.debug("POST request: %s" % str(json))

        # required
        user_ids = json["user_ids"]

        # one of them is required
        room_name = json.get("room_name")
        room_id = json.get("room_id")

        if room_name is not None:
            room_name = utils.b64d(room_name)

        return self._do_post(room_id, room_name, user_ids)
