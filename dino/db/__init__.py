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

from zope.interface import Interface

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class IDatabase(Interface):
    def is_admin(self, user_id: str) -> bool:
        """
        check if a user is an admin or not

        :param user_id: the id of the user to check
        :return: true if admin, false otherwise
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

    def room_name_exists(self, channel_id, room_name: str) -> bool:
        """
        check if a room name exists for a given channel or not

        :param channel_id: the id of the channel
        :param room_name: the name of the room to check
        :return: true if exists, false otherwise
        """

    def room_owners_contain(self, room_id, user_id) -> bool:
        """
        check if a user is an owner for a room or not

        :param room_id: the id fo the room to check for
        :param user_id: the id of the user to check
        :return: true if owner for room, false otherwise
        """

    def delete_acl(self, room_id: str, acl_type: str) -> None:
        """

        :param room_id:
        :param acl_type:
        :return:
        """

    def add_acls(self, room_id: str, acls: dict) -> None:
        """

        :param room_id:
        :param acls:
        :return:
        """

    def get_acls(self, room_id: str) -> list:
        """

        :param room_id:
        :return:
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
