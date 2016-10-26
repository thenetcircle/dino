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

        :param user_id:
        :param room_id:
        :return:
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
        :param user_id: uuid of the user
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

    def remove_owner(self, room_id: str, user_id: str) -> None:
        """
        remove the owner role from a user for a room

        :param room_id: the uuid of the room
        :param user_id: the id of the user
        :return: nothing
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

    def join_room(self, user_id: str, user_name: str, room_id: str, room_name: str) -> None:
        """
        join a room

        :param user_id: the uuid of the user joining
        :param user_name: the name of the user joining
        :param room_id: the uuid of the room to join
        :param room_name: the name of the room to join
        :return: nothing
        """

    def room_allows_cross_group_messaging(self, room_uuid: str) -> bool:
        """
        check if the room allows messages from other rooms

        :raises NoSuchRoomException if room doesn't exist
        :param room_uuid: the room to check for permission
        :return: true if allowed, false otherwise
        """

    def delete_acl(self, room_id: str, acl_type: str) -> None:
        """
        delete an acl from a room

        :raises InvalidAclTypeException if the type is invalid
        :raises NoSuchRoomException if the room doesn't exist
        :param room_id: the id of the room
        :param acl_type: deletes one acl from this room with this type
        :return: nothing
        """

    def delete_acl_channel(self, channel_id: str, acl_type: str) -> None:
        """
        delete an acl from a channel

        :raises InvalidAclTypeException if the type is invalid
        :raises NoSuchChannelException if the channel doesn't exist
        :param channel_id: the id of the channel
        :param acl_type: deletes one acl from this channel with this type
        :return: nothing
        """

    def add_acls(self, room_id: str, acls: dict) -> None:
        """
        Add acls the room.

        :raises InvalidAclTypeException if the type is invalid
        :raises InvalidAclValueException if the value doesn't validate for the type
        :raises NoSuchRoomException if room doesn't exist
        :param room_id: the room id
        :param acls:
        :return: nothing
        """

    def add_acls_channel(self, channel_id: str, acls: dict) -> None:
        """
        Add acls the channel.

        :raises InvalidAclTypeException if the type is invalid
        :raises InvalidAclValueException if the value doesn't validate for the type
        :raises NoSuchChannelException if channel doesn't exist
        :param channel_id: the channel id
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

    def get_acls_channel(self, channel_id: str) -> dict:
        """
        get the access list for a channel

        :raises NoSuchChannelException if the channel doesn't exist
        :param channel_id: the uuid of the channel
        :return: a dict of acls, empty if no acls
        """

    def get_acls(self, room_id: str) -> dict:
        """
        get the access list for a room

        :raises NoSuchRoomException if room doesn't exist
        :param room_id: the room uuid
        :return: a dict of acls, empty if no acls
        """

    def users_in_room(self, room_id: str) -> dict:
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
