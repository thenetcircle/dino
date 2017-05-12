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
    def create_admin_room(self) -> str:
        """
        create the special admin room

        :return: the newly created room's uuid
        """

    def is_room_ephemeral(self, room_id: str) -> bool:
        """
        check whether or not a room is ephemeral (temporary); rooms created by regular users are ephemeral, so if wanted
        they can be automatically removed when the owners have all left the room

        :param room_id: the uuid of the room
        :return: true if ephemeral, false otherwise
        """

    def set_ephemeral_room(self, room_id: str):
        """
        set as ephemeral room
        :param room_id: roo uuid
        :return: nothing
        """

    def unset_ephemeral_room(self, room_id: str):
        """
        unset as ephemeral room
        :param room_id: roo uuid
        :return: nothing
        """

    def add_default_room(self, room_id: str) -> None:
        """
        set as default room

        :param room_id: room uuid
        :return: nothing
        """

    def remove_default_room(self, room_id: str) -> None:
        """
        unset as default room

        :param room_id: room uuid
        :return: nothing
        """

    def add_words_to_blacklist(self, words: list) -> None:
        """
        add new words to the blacklist

        :param words: a list of words to add
        :return: nothing
        """

    def remove_word_from_blacklist(self, word_id) -> None:
        """
        remove a word from the blacklist

        :param word_id: the id (primary key) of the word to remove
        :return: nothing
        """

    def get_black_list_with_ids(self) -> list:
        """
        same as get_black_list() but a list instead including the IDs of the words

        :return: a list of forbidden words, e.g. [{'id':1,'word':'foo'},{'id':2,'word':'bar'}]
        """

    def get_black_list(self) -> set:
        """
        get the list of blacklisted words for sending messages

        :return: a set of forbidden words, e.g. {'foo','bar'}
        """

    def search_for_users(self, query: str) -> list:
        """
        search for a user by id or name (query can match any of them, insensitive)

        :param query: a string to match
        :return: a list of user dicts, e.g. {'uuid':'<uuid>','name':'foo'}
        """

    def get_admin_room(self) -> str:
        """
        get the uuid of the admin room , or None of not found

        :return: the uuid of the admin room, or None of not found
        """

    def get_online_admins(self) -> list:
        """
        get uuids of all admins that are online

        :return: list of uuids
        """

    def get_user_roles_in_room(self, user_id: str, room_id: str) -> list:
        """
        the the roles in only one room for a user, e.g.:

            [
                "owner",
                "admin"
            ]

        :param user_id: the id of the user
        :param room_id: the uuid of the room
        :return: a list of strings, roles for that room
        """

    def get_reason_for_ban_global(self, user_id: str) -> str:
        """
        get the reason for a global ban, or empty string if no reason found

        :param user_id: uuid of the user
        :return: the reason string, or blank string if not found
        """

    def get_reason_for_ban_channel(self, user_id: str, channel_uuid: str) -> str:
        """
        get the reason for a ban in a room, or empty string if no reason found

        :param user_id: uuid of the user
        :param channel_uuid: uuid of the channel
        :return: the reason string, or blank string if not found
        """

    def get_reason_for_ban_room(self, user_id: str, room_uuid: str) -> str:
        """
        get the reason for a ban in a room, or empty string if no reason found

        :param user_id: uuid of the user
        :param room_uuid: uuid of the room
        :return: the reason string, or blank string if not found
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

    def get_channels(self) -> dict:
        """
        get all channels on the server

        :return: a dict of channels: {'<channel UUID>': '<channel name>'}]
        """

    def channel_exists(self, channel_id) -> bool:
        """
        check if a channel exists or not

        :param channel_id: the id of the channel to check
        :return: true if exists, false otherwise
        """

    def rooms_for_channel(self, channel_id) -> dict:
        """
        get all rooms for a specific channel

        :param channel_id: the id of the channel to find the rooms for
        :return: a dict of rooms: {'<room UUID>': '<room name>'}
        """

    def channel_for_room(self, room_id: str) -> str:
        """
        get the channel for a room

        :param room_id: the id of the room to get the channel for
        :return: the channel uuid, or raises NoChannelFoundException if not found
        """

    def channel_name_exists(self, channel_name: str) -> bool:
        """
        check if a channel name exists or not

        :param channel_name: the name of the channel to check
        :return: true if exists, false otherwise
        """

    def room_name_exists(self, channel_id, room_name: str) -> bool:
        """
        check if a room name exists for a given channel or not

        :param channel_id: the id of the channel
        :param room_name: the name of the room to check
        :return: true if exists, false otherwise
        """

    def room_exists(self, channel_id: str, room_id: str) -> bool:
        """
        check if a room exists for a given channel

        :param channel_id: the id of the channel
        :param room_id: the id of the room
        :return: true if exists, false otherwise
        """

    def room_contains(self, room_id: str, user_id: str) -> bool:
        """
        check if a user is in a room or not

        :raises NoSuchRoomException if the room can't be found
        :param room_id: the uuid of the room
        :param user_id: the id of the user
        :return: true if in room, false otherwsie
        """

    def create_room(self, room_name: str, room_id: str, channel_id: str, user_id: str, user_name) -> None:
        """
        create a new room (user_id will become the owner of the the new room)

        :param room_name: the name of the room
        :param room_id: the uuid of the room
        :param channel_id: the uuid of the channel
        :param user_id: the uuid of the user creating the room
        :param user_name: the name of the user creating the room
        :return: nothing
        """

    def remove_channel(self, channel_id: str) -> None:
        """
        remove a channel

        :param channel_id: the uuid of the channel to remove
        :return: nothing
        """

    def remove_room(self, channel_id: str, room_id: str) -> None:
        """
        remove a room

        :raises NoSuchChannel exception if the channel doesn't exist
        :raises NoSuchRoom exception if the room doesn't exist
        :param channel_id: the uuid of the channel
        :param room_id: the uuid of the room
        :return: nothing
        """

    def leave_room(self, user_id: str, room_id: str) -> None:
        """
        leave a room

        :param user_id: the id of the user leaving
        :param room_id: the uuid of the room to leave
        :return:
        """

    def remove_global_ban(self, user_id: str) -> str:
        """
        remove a global ban for a user, e.g. when the ban has expired

        :param user_id: the id of the user
        :return: nothing
        """

    def remove_channel_ban(self, channel_id: str, user_id: str) -> str:
        """
        remove a channel ban for a user, e.g. when the ban has expired

        :param channel_id: the uuid of the channel
        :param user_id: the id of the user
        :return:
        """

    def remove_room_ban(self, room_id: str, user_id: str) -> str:
        """
        remove a room ban for a user, e.g. when the ban has expired

        :param room_id: the uuid of the room
        :param user_id: the id of the user
        :return:
        """

    def get_global_ban_timestamp(self, user_id: str) -> (str, str, str):
        """
        get the duration, timestamp and username for a global ban of this user

        :param user_id: the id of the user
        :return: (duration, timestamp, username) or (None, None, None) if no such ban
        """

    def get_channel_ban_timestamp(self, channel_id: str, user_id: str) -> (str, str, str):
        """
        get the duration, timestamp and username for a channel ban of this user

        :param user_id: the id of the user
        :param channel_id: the uuid of the channel
        :return: (duration, timestamp, username) or (None, None, None) if no such ban
        """

    def get_room_ban_timestamp(self, room_id: str, user_id: str) -> (str, str, str):
        """
        get the duration, timestamp and username for a room ban of this user

        :param user_id: the id of the user
        :param room_id: the uuid of the room
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

    def get_banned_users_for_channel(self, channel_id: str) -> dict:
        """
        get all users banned from this channel

        :param channel_id: the uuid of the room
        :return: a dict of {"<user_id>": {"duration": "<duration time>", "timestamp": "<ban end timestamp>"}
        """

    def get_banned_users_for_room(self, room_id: str) -> dict:
        """
        get all users banned from this room

        :param room_id: the uuid of the room
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

    def ban_user_channel(self, user_id: str, ban_timestamp: str, ban_duration: str, channel_id: str, reason: str=None, banner_id: str=None) -> None:
        """
        ban a user from either a channel

        :param user_id: the id of the user to ban
        :param ban_timestamp: end time of the ban
        :param ban_duration: how long this ban is for
        :param channel_id: the uuid of the channel to ban for
        :param reason: optional free-text reason for the ban
        :param banner_id: optional user if of the one who banned
        :return: nothing
        """

    def ban_user_room(self, user_id: str, ban_timestamp: str, ban_duration: str, room_id: str, reason: str=None, banner_id: str=None) -> None:
        """
        ban a user from either a room

        :param user_id: the id of the user to ban
        :param ban_timestamp: end time of the ban
        :param ban_duration: how long this ban is for
        :param room_id: the uuid of the room to ban for
        :param reason: optional free-text reason for the ban
        :param banner_id: optional user if of the one who banned
        :return: nothing
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

    def kick_user(self, room_id: str, user_id: str) -> None:
        """
        kick a user from a room

        :param room_id: the uuid of the room to kick the user from
        :param user_id: the id of the user to kick
        :return: nothing
        """

    def is_banned_globally(self, user_id: str) -> (bool, Union[str, None]):
        """
        check if a user is banned globally or not

        :param user_id: the id of the user
        :return: "True, <end datetime sting>" or "False, None"
        """

    def is_banned_from_channel(self, channel_id: str, user_id: str) -> (bool, Union[str, None]):
        """
        check if a user is banned from a channel or not

        :param user_id: the id of the user
        :param channel_id: the uuid of the channel
        :return: "True, <end datetime sting>" or "False, None"
        """

    def is_banned_from_room(self, room_id: str, user_id: str) -> (bool, Union[str, None]):
        """
        check if a user is banned from a room or not

        :param user_id: the id of the user
        :param room_id: the uuid of the room
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

    def is_owner(self, room_id: str, user_id: str) -> bool:
        """
        check if a user is an owner of a room

        :param room_id: uuid of the room
        :param user_id: uuid of the user
        :return: true or false
        """

    def is_owner_channel(self, channel_id: str, user_id: str) -> bool:
        """
        check if a user is an owner of a channel

        :param channel_id: uuid of the channel
        :param user_id: uuid of the user
        :return: true or false
        """

    def is_super_user(self, user_id: str) -> bool:
        """
        check if a user is a global super admin or not

        :param user_id: the uuid of the user to check for
        :return: true if super user, false otherwise
        """

    def remove_admin(self, channel_id: str, user_id: str) -> None:
        """
        remove the admin role from a user for a channel

        :param channel_id: the uuid of the channel
        :param user_id: the id of the user
        :return: nothing
        """

    def remove_owner_channel(self, channel_id: str, user_id: str) -> None:
        """
        remove the owner role from a user for a channel

        :param channel_id: the uuid of the channel
        :param user_id: the id of the user
        :return: nothing
        """

    def remove_moderator(self, room_id: str, user_id: str) -> None:
        """
        remove the moderator role from a user for a room

        :param room_id: the uuid of the room
        :param user_id: the id of the user
        :return: nothing
        """

    def remove_global_moderator(self, user_id: str) -> None:
        """
        remove the global moderator status for a user

        :param user_id: the id of the user
        :return: nothing
        """

    def remove_owner(self, room_id: str, user_id: str) -> None:
        """
        remove the owner role from a user for a room

        :param room_id: the uuid of the room
        :param user_id: the id of the user
        :return: nothing
        """

    def set_sid_for_user(self, user_id: str, sid: str) -> None:
        """
        set the sid (session id) generated by flask for this user

        :param user_id: the id of the user
        :param sid: the session id from flask
        :return: nothing
        """

    def get_sid_for_user(self, user_id: str) -> Union[str, None]:
        """
        get the sid (session id) generated by flask for this user

        :param user_id: the id of the user
        :return: the session id for this user, if it exists, otherwise None
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

    def get_owners_channel(self, channel_id: str) -> dict:
        """
        get all owners of a channel

        :raises NoSuchRoomException if channel can't be found
        :param channel_id: the uuid of the channel
        :return: a dict of user_id -> user_name
        """

    def get_admins_channel(self, channel_id: str) -> dict:
        """
        get all admins of a channel

        :raises NoSuchRoomException if channel can't be found
        :param channel_id: the uuid of the channel
        :return: a dict of user_id -> user_name
        """

    def get_owners_room(self, room_id: str) -> dict:
        """
        get all owners of a room

        :raises NoSuchRoomException if room can't be found
        :param room_id: the uuid of the room
        :return: a dict of user_id -> user_name
        """

    def get_moderators_room(self, room_id: str) -> dict:
        """
        get all moderators of a room

        :raises NoSuchRoomException if room can't be found
        :param room_id: the uuid of the room
        :return: a dict of user_id -> user_name
        """

    def set_owner(self, room_id: str, user_id: str) -> None:
        """
        set role owner on a room to a user

        :param room_id: uuid of the room
        :param user_id: uuid of the user
        :return: nothing
        """

    def set_owner_channel(self, channel_id: str, user_id: str) -> None:
        """
        set role owner on a room to a user

        :param channel_id: uuid of the room
        :param user_id: uuid of the user
        :return: nothing
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

    def create_channel(self, channel_name, channel_id, user_id) -> None:
        """
        create a new channel

        :param channel_name: name of the channel
        :param channel_id: uuid of the channel
        :param user_id: uuid of the user creating the channel
        :return: nothing
        """

    def update_channel_sort_order(self, channel_uuid: str, sort: int) -> None:
        """
        update the sort order of a channel

        :param channel_uuid: uuid of the channel
        :param sort: integer value to be sorted by (ascending)
        :return: nothing
        """

    def update_room_sort_order(self, room_uuid: str, sort: int) -> None:
        """
        update the sort order of a room

        :param room_uuid: uuid of the room
        :param sort: integer value to be sorted by (ascending)
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

    def delete_acl_in_channel_for_action(self, channel_id: str, acl_type: str, action: str) -> None:
        """
        delete an acl in a channel for a certain action

        :raises InvalidApiActionException if the api action is invalid
        :raises NoSuchChannelException if the channel doesn't exist
        :param channel_id: the uuid of the channel
        :param acl_type: the type of the acl (e.g. gender/membership etc.)
        :param action: the action to delete for (e.g. join/kick/history etc.)
        :return: nothing
        """

    def delete_acl_in_room_for_action(self, room_id: str, acl_type: str, action: str) -> None:
        """
        delete an acl in a room for a certain action

        :raises InvalidApiActionException if the api action is invalid
        :raises NoSuchRoomException if the room doesn't exist
        :param room_id: the uuid of the room
        :param acl_type: the type of the acl (e.g. gender/membership etc.)
        :param action: the action to delete for (e.g. join/kick/history etc.)
        :return: nothing
        """

    def update_acl_in_channel_for_action(self, channel_id: str, action: str, acl_type: str, acl_value: str) -> None:
        """
        change the value of an acl for a channel

        :raises InvalidApiActionException if the api action is invalid
        :raises InvalidAclTypeException if the type is invalid
        :raises InvalidAclValueException if the value doesn't validate for the type
        :raises NoSuchChannelException if the channel doesn't exist
        :param channel_id: the channel uuid of the room
        :param action: the api action (kick/join etc)
        :param acl_type: the acl type
        :param acl_value: the new value for the acl type
        :return: nothing
        """

    def update_acl_in_room_for_action(self, channel_id: str, room_id: str, action: str, acl_type: str, acl_value: str) -> None:
        """
        change the value of an acl for a room

        :raises InvalidApiActionException if the api action is invalid
        :raises InvalidAclTypeException if the type is invalid
        :raises InvalidAclValueException if the value doesn't validate for the type
        :raises NoSuchRoomException if room doesn't exist
        :param channel_id: the channel uuid
        :param room_id: the room uuid
        :param action: the api action (kick/join etc)
        :param acl_type: the acl type
        :param acl_value: the new value for the acl type
        :return: nothing
        """

    def add_acls_in_room_for_action(self, room_id: str, action: str, acls: dict) -> None:
        """
        Add acls the room.

        :raises InvalidApiActionException if the api action is invalid
        :raises InvalidAclTypeException if the type is invalid
        :raises InvalidAclValueException if the value doesn't validate for the type
        :raises NoSuchRoomException if room doesn't exist
        :param room_id: the room uuid
        :param action: the api action (kick/join etc)
        :param acls:
        :return: nothing
        """

    def add_acls_in_channel_for_action(self, channel_id: str, action: str, acls: dict) -> None:
        """
        Add acls the channel.

        :raises InvalidApiActionException if the api action is invalid
        :raises InvalidAclTypeException if the type is invalid
        :raises InvalidAclValueException if the value doesn't validate for the type
        :raises NoSuchChannelException if channel doesn't exist
        :param channel_id: the channel id
        :param action: the api action (kick/join etc)
        :param acls:
        :return: nothing
        """

    def get_last_read_timestamp(self, room_id: str, user_id: str) -> int:
        """
        get the last read timestamp for a user in a group

        :param room_id: the uuid of the room
        :param user_id: the uuid of the user
        :return:
        """

    def update_last_read_for(self, users: set, room_id: str, time_stamp: int) -> None:
        """
        update the last read timestamp of a room for a set of users

        :param users: a set of users to update the last read timestamp for
        :param room_id: the uuid of the room for which this timestamp should be set
        :param time_stamp: the timestamp to set
        :return: nothing
        """

    def get_acl_validation_value(self, acl_type: str, validation_method: str) -> str:
        """
        get the validation value for this type from the database

        :param acl_type: the type of the acl
        :param validation_method: the method of validation (e.g. str_in_csv)
        :return: the
        """

    def get_all_acls_channel(self, channel_id: str) -> dict:
        """
        get all acls for a channel, seperated by actions

        example response:

        {
            'list': {
                'gender': 'm,f'
            },
            'create': {
                'moderator': 'y'
            }
        }

        :param channel_id: the uuid of the channel
        :return: a dict with acls separated by action
        """

    def get_all_acls_room(self, room_id: str) -> dict:
        """
        get all acls for a room, seperated by actions

        example response:

        {
            'message': {
                'gender': 'm,f'
            },
            'kick': {
                'moderator': 'y'
            }
        }

        :param room_id: the uuid of the room
        :return: a dict with acls separated by action
        """

    def get_acls_in_room_for_action(self, room_id: str, action: str) -> dict:
        """
        get acls in a room with a certain action (join/kick/message etc.)

        :param room_id: the uuid of the room
        :param action: the action to get acls for
        :return: a dict of acls for this action
        """

    def get_acls_in_channel_for_action(self, channel_id: str, action: str) -> dict:
        """
        get acls in a channel with a certain action (join/kick/message etc.)

        :param channel_id: the uuid of the channel
        :param action: the action to get acls for
        :return: a dict of acls for this action
        """

    def users_in_room(self, room_id: str, user_id: str=None) -> dict:
        """
        get a dict of {user_id: user_name} of users in the given room

        :raises NoSuchRoomException if room doesn't exist
        :param room_id: the uuid of the room
        :return: a dict with users
        """

    def rooms_for_user(self, user_id: str = None) -> dict:
        """
        get all rooms that a user is in

        :param user_id: the id of the user
        :return: a dict of rooms: {'<room id>': '<room name>'}
        """

    def remove_current_rooms_for_user(self, user_id: str) -> None:
        """
        removes all rooms for the user

        :param user_id: the id of the user
        :return: nothing
        """

    def get_default_rooms(self) -> list:
        """
        get a list of uuids for default rooms (auto-join)

        :return: a list of room uuids
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

    def get_room_name(self, room_id: str) -> str:
        """
        get the name of a room from its id

        :raises NoSuchRoomException if no room found with the given id
        :param room_id: the uuid of the room
        :return: the name of the room
        """

    def rename_channel(self, channel_id: str, channel_name: str) -> None:
        """
        rename a channel

        :raises NoSuchChannelException if the channel doesn't exist
        :param channel_id: the uuid of the channel to rename
        :param channel_name: the new name to set for the channel
        :return: nothing
        """

    def rename_room(self, channel_id: str, room_id: str, room_name: str) -> None:
        """
        rename a channel

        :raises NoSuchRoomException if the room doesn't exist
        :param channel_id: the uuid of the channel for this room
        :param room_id: the uuid of the room to rename
        :param room_name: the new name to set for the room
        :return: nothing
        """

    def get_channel_name(self, channel_id: str) -> str:
        """
        get the name of a channel from its id

        :raises NoSuchRoomException if no channel found with the given id
        :param channel_id: the uuid of the channel
        :return: the name of the channel
        """

    def create_user(self, user_id: str, user_name: str) -> None:
        """
        create a new user

        :raises UserExistsException if the user id already exists
        :param user_id: the desired id of the user
        :param user_name: the name of the user
        :return: nothing
        """
