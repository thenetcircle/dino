import logging
from datetime import datetime
from uuid import uuid4 as uuid

from dino.utils import b64d
from flask import request

from dino import environ
from dino.rest.resources.base import RoomNameBaseResource
from dino.utils.decorators import timeit

logger = logging.getLogger(__name__)


class CreateRoomResource(RoomNameBaseResource):
    def __init__(self):
        super(CreateRoomResource, self).__init__(environ.env)
        self.last_cleared = datetime.utcnow()
        self.request = request
        self.namespace = "/ws"

    def _do_post(self, room_name, user_ids, owner_id, owner_name, channel_id):
        room_id = str(uuid())

        if channel_id is None:
            channel_id = environ.env.db.get_or_create_default_channel()

        environ.env.db.create_room(room_name, room_id, channel_id, owner_id, owner_name, ephemeral=True)
        environ.env.db.set_owner(room_id, owner_id)

        for user_id in user_ids:
            self.join(user_id, room_id)

        return {
            "room_id": room_id,
            "room_name": room_name,
            "channel_id": channel_id
        }

    @timeit(logger, "on_rest_create_room")
    def do_post(self):
        is_valid, msg, json = self.validate_json(self.request, silent=False)
        if not is_valid:
            raise AttributeError(msg)

        logger.debug("POST request: %s" % str(json))

        room_name = b64d(json["room_name"])
        user_ids = json["user_ids"]
        owner_id = json["owner_id"]
        owner_name = b64d(json["owner_name"])

        # optional, will use default if not specified
        channel_id = json.get("channel_id")

        return self._do_post(room_name, user_ids, owner_id, owner_name, channel_id)
