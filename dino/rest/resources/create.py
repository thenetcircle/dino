import logging
from datetime import datetime
from uuid import uuid4 as uuid

from activitystreams import parse as parse_to_as
from flask import request

from dino import environ
from dino.rest.resources.base import BaseResource
from dino.utils import ActivityBuilder
from dino.utils.decorators import timeit

logger = logging.getLogger(__name__)


def join_activity(actor_id: str, target_id: str, session_ids: list, namespace: str) -> dict:
    return ActivityBuilder.enrich({
        "actor": {
            "id": actor_id,
            "content": ",".join(session_ids),
            "url": namespace
        },
        "verb": "join",
        "target": {
            "id": target_id
        }
    })


class CreateRoomResource(BaseResource):
    def __init__(self):
        super(CreateRoomResource, self).__init__()
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
            session_ids = environ.env.db.get_sids_for_user(user_id)

            if len(session_ids) == 0:
                logger.warning("no sessions found for user {}, can not auto-join created room".format(user_id))
                continue

            if len(session_ids) > 1:
                logger.warning("multiple session ids found for user {}, will make all join".format(user_id))

            data = join_activity(user_id, room_id, session_ids, self.namespace)
            activity = parse_to_as(data)

            # reuse existing logic for joining the room
            environ.env.observer.emit("on_join", (data, activity))

    @timeit(logger, "on_rest_create_room")
    def do_post(self):
        is_valid, msg, json = self.validate_json(self.request, silent=False)
        if not is_valid:
            raise AttributeError(msg)

        logger.debug("POST request: %s" % str(json))

        room_name = json["room_name"]
        user_ids = json["user_ids"]
        owner_id = json["owner_id"]
        owner_name = json["owner_name"]

        # optional, will use default if not specified
        channel_id = json.get("channel_id")

        return self._do_post(room_name, user_ids, owner_id, owner_name, channel_id)
