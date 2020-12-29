import logging
from datetime import datetime

from activitystreams import parse as parse_to_as
from flask import request

from dino import environ
from dino import utils
from dino import validation
from dino.config import ApiActions, ApiTargets
from dino.exceptions import NoSuchRoomException
from dino.rest.resources.base import BaseResource
from dino.utils.decorators import timeit

logger = logging.getLogger(__name__)


class RoomsAclResource(BaseResource):
    def __init__(self):
        super(RoomsAclResource, self).__init__()
        self.last_cleared = datetime.utcnow()
        self.request = request
        self.env = environ.env

    @timeit(logger, "on_rest_rooms")
    def _do_get(self, user_id):
        channels = self.env.db.get_channels()
        activity = parse_to_as({
            "actor": {
                "id": user_id
            },
            "target": dict(),
            "verb": "filter"
        })

        logger.info("channels {}".format(channels))

        # filter_channels_by_acl() expects channels in a certain format
        temp_activity = utils.activity_for_list_channels(channels)
        channels_with_acl = temp_activity["object"]["attachments"]

        logger.info("channels_with_acl {}".format(channels_with_acl))

        # filter the channels and replace it on the activity we created
        filtered_channels = utils.filter_channels_by_acl(activity, channels_with_acl, env_to_use=self.env)
        filtered_rooms = dict()
        channel_names = dict()
        
        for channel in filtered_channels:
            channel_id = channel["id"]
            channel_names[channel_id] = self.env.db.get_channel_name(channel_id)
            all_rooms_in_channel = self.env.db.rooms_for_channel(channel_id)

            for room_id, room in all_rooms_in_channel.items():
                room["id"] = room_id

                try:
                    acls = utils.get_acls_in_room_for_action(room_id, ApiActions.JOIN)
                except NoSuchRoomException:
                    continue

                activity.target.id = room_id
                is_valid, error_msg = validation.acl.validate_acl_for_action(
                    activity, 
                    ApiTargets.ROOM, 
                    ApiActions.JOIN, 
                    acls,
                    object_type=ApiTargets.ROOM,
                    env_to_use=self.env
                )
                if not is_valid:
                    logger.info("user {} is not allowed to join room {}".format(user_id, room_id))
                    continue

                is_banned, info_dict = utils.is_banned(user_id, room_id)
                if is_banned:
                    logger.info("user {} is banned from room {}".format(user_id, room_id))
                    continue

                if channel_id not in filtered_rooms:
                    filtered_rooms[channel_id] = list()

                filtered_rooms[channel_id].append(room)

        formatted_rooms = list()
        for channel_id, rooms in filtered_rooms.items():
            for room in rooms:
                formatted_rooms.append({
                    "status": "temporary" if room["ephemeral"] else "static",
                    "users": room["users"],
                    "room_id": room["id"],
                    "room_name": room["name"],
                    "channel_name": channel_names.get(channel_id, ""),
                    "channel_id": channel_id,
                })

        return formatted_rooms

    def do_get_with_params(self, user_id):
        return self._do_get(user_id)

    @timeit(logger, "on_rest_rooms_acl")
    def do_get(self):
        is_valid, msg, json = self.validate_json(self.request, silent=False)
        if not is_valid:
            logger.error("invalid json: %s" % msg)
            return dict()

        if "user_id" not in json:
            return dict()
        logger.debug("GET request: %s" % str(json))

        return self.do_get_with_params(json["user_id"])

    def _get_lru_method(self):
        return self.do_get_with_params

    def _get_last_cleared(self):
        return self.last_cleared

    def _set_last_cleared(self, last_cleared):
        self.last_cleared = last_cleared
