#!/usr/bin/env python

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Union
from zope.interface import Interface

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class IDatabase(Interface):
    def get_users_roles(self, user_ids: list) -> None:
        """
        will get and cache all roles for all users, only used for cache warm up during deployment

        :param user_ids: a list of user ids
        :return: nothing
        """

    def get_all_user_ids(self) -> list:
        """
        get the ids of all users, only used for cache warm up during deployment

        :return: nothing
        """

    def get_user_roles(self, user_id: str) -> dict:
        """
        get a all roles for a user (admin, mod, etc.)

        example response:

            {
                "global": [
                    "superuser"
                ],
                "channel": {
                    "<uuid of channel>": [
                        "owner",
                        "admin"
                    ],
                    "<uuid of channel>": [
                        "owner"
                    ]
                },
                "room": {
                    "<uuid of room>": [
                        "owner",
                        "moderator"
                    ],
                    "<uuid of room>": [
                        "moderator"
                    ]
                }
            }

        :param user_id:
        :return:
        """

    def leave_room(self, user_id: str, room_id: str) -> None:
        """
        leave a room

        :param user_id: the id of the user leaving
        :param room_id: the uuid of the room to leave
        :return:
        """

    def get_global_ban_timestamp(self, user_id: str) -> (str, str, str):
        """
        get the duration, timestamp and username for a global ban of this user

        :param user_id: the id of the user
        :return: (duration, timestamp, username) or (None, None, None) if no such ban
        """

    def get_bans_for_user(self, user_id: str) -> dict:
        """
        get all channel and room bans for this user, mostly used for the rest api

        return format is:

            {
                "global": {
                    "timestamp": "2016-11-29T11:30:21Z",
                    "duration": "5m"
                }
                "channel": {
                    "<channel uuid>": {
                        "timestamp": "2016-11-29T12:51:09Z",
                        "duration": "2d",
                        "name": "<channel name>"
                    }
                },
                "room" {
                    "<room uuid>": {
                        "timestamp": "2016-11-29T12:51:09Z",
                        "duration": "12h",
                        "name": "<room name>"
                    }
                }
            }

        :param user_id: the uuid of the user
        :return: a dict of bans
        """

    def get_user_ban_status(self, room_id: str, user_id: str) -> dict:
        """
        get the ban status of a user for a room

        will return status based on global ban, and status of ban for the channel of the room and for the room:

            {
                "global": "2016-11-29T11:30:21Z",
                "channel": "2016-11-29T12:51:09Z",
                "room": "2016-12-01T01:00:00Z"
            }

        or if no bans:

            {
                "global": "",
                "channel": "",
                "room": ""
            }

        :param room_id: the uuid of the room
        :param user_id: the id of the user
        :return: a dict with possible bans for global, channel and room
        """

    def get_banned_users_global(self) -> dict:
        """
        get all users banned globally

        :return: a dict of {"<user_id>": {"duration": "<duration time>", "timestamp": "<ban end timestamp>"}
        """

    def get_banned_users(self) -> dict:
        """
        get all banned users, both globally and for each room

        example return value:

            {
                "global": {
                    "<user_id>": {
                        "duration": "<duration time>",
                        "timestamp": "<ban end timestamp>"
                    }
                },
                "channels": {
                    "<channel_uuid>": {
                        "name": "<channel name>",
                        "users": {
                            "<user_id>": {
                                "name": "<user name>",
                                "duration": "<duration time>",
                                "timestamp": "<ban end timestamp>"
                            }
                        }
                    }
                },
                "rooms": {
                    "<room_uuid>": {
                        "name": "<room name>",
                        "users": {
                            "<user_id>": {
                                "name": "<user name>",
                                "duration": "<duration time>",
                                "timestamp": "<ban end timestamp>"
                            }
                        }
                    }
                }
            }

        :return: a dict with banned users
        """

    def ban_user_global(self, user_id: str, ban_timestamp: str, ban_duration: str, reason: str=None, banner_id: str=None) -> None:
        """
        ban a user globally

        :param user_id: the id of the user to ban
        :param ban_timestamp: end time of the ban
        :param ban_duration: how long this ban is for
        :param room_id: the uuid of the room to ban for, or blank if global ban
        :param reason: optional free-text reason for the ban
        :param banner_id: optional user if of the one who banned
        :return: nothing
        """

    def is_banned_globally(self, user_id: str) -> (bool, Union[str, None]):
        """
        check if a user is banned globally or not

        :param user_id: the id of the user
        :return: "True, <end datetime sting>" or "False, None"
        """

    def is_admin(self, channel_id: str, user_id: str) -> bool:
        """
        check if a user is an admin of a channel

        :param channel_id: uuid of the channel
        :param user_id: uuid of the user
        :return: true or false
        """

    def is_moderator(self, room_id: str, user_id: str) -> bool:
        """
        check if a user is a moderator of a room

        :param room_id: uuid of the room
        :param user_id: id of the user
        :return: true or false
        """

    def is_global_moderator(self, user_id: str) -> bool:
        """
        check if a user is a global moderator

        :param user_id: the id of the user
        :return: true or false
        """

    def is_super_user(self, user_id: str) -> bool:
        """
        check if a user is a global super admin or not

        :param user_id: the uuid of the user to check for
        :return: true if super user, false otherwise
        """

    def add_sid_for_user(self, user_id: str, sid: str) -> None:
        """
        add a sid (session id) generated by flask for this user

        :param user_id: the id of the user
        :param sid: a session id from flask
        :return: nothing
        """

    def reset_sids_for_user(self, user_id: str) -> None:
        """
        remove all sids (session id) generated by flask for this user

        :param user_id: the id of the user
        :return: nothing
        """

    def remove_sid_for_user(self, user_id: str, sid: str) -> None:
        """
        remove a sid (session id) generated by flask for this user

        :param user_id: the id of the user
        :param sid: a session id from flask
        :return: nothing
        """

    def get_sids_for_user(self, user_id: str) -> Union[list, None]:
        """
        get the sid(s) (session id) generated by flask for this user

        :param user_id: the id of the user
        :return: the session id(s) for this user, if it exists, otherwise None
        """

    def set_user_name(self, user_id: str, user_name: str) -> str:
        """
        set the user name for this id

        :param user_id: the uuid of the user
        :param user_name: the name of the user
        :return: nothing
        """

    def get_user_name(self, user_id: str) -> str:
        """
        the the user name from user id

        :raises NoSuchUserException if a name can't be found
        :param user_id: the uuid of the user
        :return: the user name
        """

    def set_moderator(self, room_id: str, user_id: str) -> None:
        """
        set role moderator on room to a user

        :param room_id: the uuid of the room
        :param user_id: the uuid of the user
        :return: nothing
        """

    def set_global_moderator(self, user_id: str) -> None:
        """
        set a user as a global moderator

        :param user_id: the id of the user
        :return: nothing
        """

    def set_admin(self, channel_id: str, user_id: str) -> None:
        """
        set role admin on channel to a user

        :param channel_id: the uuid of the channel
        :param user_id: the uuid of the user
        :return: nothing
        """

    def get_super_users(self) -> dict:
        """
        get a dict of super users in the form of {user_id: user_name}

        :return: a dict of super users
        """

    def set_super_user(self, user_id: str) -> None:
        """
        set role super user globally for a user

        :param user_id: the uuid of the user
        :return: nothing
        """

    def remove_super_user(self, user_id: str) -> None:
        """
        remove super user status from a user

        :param user_id: the id of the user to remove the status from
        :return: nothing
        """

    def join_room(self, user_id: str, user_name: str, room_id: str, room_name: str) -> None:
        """
        join a room

        :param user_id: the uuid of the user joining
        :param user_name: the name of the user joining
        :param room_id: the uuid of the room to join
        :param room_name: the name of the room to join
        :return: nothing
        """

    def get_user_status(self, user_id: str) -> str:
        """
        the the status of the user (online/offline/invisible)

        :param user_id: the id of the user
        :return: the status
        """

    def set_user_offline(self, user_id: str) -> None:
        """
        indicate a user is offline

        :param user_id: id of the user
        :return: nothing
        """

    def set_user_online(self, user_id: str) -> None:
        """
        indicate a user is online

        :param user_id: id of the user
        :return: nothing
        """

    def set_user_invisible(self, user_id: str) -> None:
        """
        indicate a user is invisible

        :param user_id: id of the user
        :return: nothing
        """

    def create_user(self, user_id: str, user_name: str) -> None:
        """
        create a new user

        :raises UserExistsException if the user id already exists
        :param user_id: the desired id of the user
        :param user_name: the name of the user
        :return: nothing
        """
