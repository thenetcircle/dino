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


class ICache(Interface):
    def set_global_ban_timestamp(self, user_id: str, duration: str, timestamp: str, username: str) -> None:
        """
        set the global ban timestamp for a user to a given timestamp

        :param user_id: the id of the user
        :param duration: the duration, e.g. 12d
        :param timestamp: the timestamp
        :param username: the username of this user
        :return: nothing
        """

    def set_channel_ban_timestamp(self, channel_id: str, user_id: str, duration: str, timestamp: str, username: str) -> None:
        """
        set the ban timestamp on channel for a user to a given timestamp

        :param user_id: the id of the user
        :param channel_id: the uuid of the channel
        :param duration: the duration, e.g. 12d
        :param timestamp: the timestamp
        :param username: the username of this user
        :return: nothing
        """

    def set_room_ban_timestamp(self, room_id: str, user_id: str, duration: str, timestamp: str, username: str) -> None:
        """
        set the ban timestamp on a room for a user to a given timestamp

        :param user_id: the id of the user
        :param room_id: the uuid of the room
        :param duration: the duration, e.g. 12d
        :param timestamp: the timestamp
        :param username: the username of this user
        :return: nothing
        """

    def get_global_ban_timestamp(self, user_id: str) -> str:
        """
        get the ban timestamp of the user in the given room, or empty string if no ban exist

        :param user_id: the id of the user
        :return: the timestamp in ConfigKeys.DEFAULT_DATE_FORMAT format, or '' if no ban exists
        """

    def get_channel_ban_timestamp(self, channel_id: str, user_id: str) -> str:
        """
        get the ban timestamp of the user in the given channel, or empty string if no ban exist

        :param channel_id: the uuid of the channel
        :param user_id: the id of the user
        :return: the timestamp in ConfigKeys.DEFAULT_DATE_FORMAT format, or '' if no ban exists
        """

    def get_room_ban_timestamp(self, room_id: str, user_id: str) -> str:
        """
        get the ban timestamp of the user in the given room, or empty string if no ban exist

        :param room_id: the uuid of the room
        :param user_id: the id of the user
        :return: the timestamp in ConfigKeys.DEFAULT_DATE_FORMAT format, or '' if no ban exists
        """

    def get_room_id_for_name(self, channel_id: str, room_name: str) -> str:
        """

        :param channel_id:
        :param room_name:
        :return:
        """

    def set_room_id_for_name(self, channel_id, room_name, room_id):
        """

        :param channel_id:
        :param room_name:
        :param room_id:
        :return:
        """

    def get_user_name(self, user_id: str) -> str:
        """
        the the name of the user from the id

        :param user_id: the id of the user
        :return: the name of the user
        """

    def set_user_name(self, user_id: str, user_name: str) -> None:
        """
        set the name of a user in the cache

        :param user_id: the id of the user
        :param user_name: the name of the user
        :return: nothing
        """

    def get_room_exists(self, channel_id, room_id):
        """

        :param channel_id:
        :param room_id:
        :return:
        """

    def get_channel_name(self, channel_id: str) -> str:
        """

        :param channel_id:
        :return:
        """

    def get_room_name(self, room_id: str) -> str:
        """

        :param room_id:
        :return:
        """

    def set_room_exists(self, channel_id, room_id, room_name):
        """

        :param channel_id:
        :param room_id:
        :param room_name:
        :return:
        """

    def set_channel_exists(self, channel_id: str) -> None:
        """

        :param channel_id:
        :return:
        """

    def set_channel_for_room(self, channel_id: str, room_id: str) -> None:
        """

        :param channel_id:
        :param room_id:
        :return:
        """

    def get_channel_exists(self, channel_id):
        """

        :param channel_id:
        :return:
        """

    def get_channel_for_room(self, room_id):
        """

        :param room_id:
        :return:
        """

    def get_user_status(self, user_id: str):
        """

        :param user_id:
        :return:
        """

    def user_check_status(self, user_id, other_status):
        """

        :param user_id:
        :param other_status:
        :return:
        """

    def user_is_offline(self, user_id):
        """

        :param user_id:
        :return:
        """

    def user_is_online(self, user_id):
        """

        :param user_id:
        :return:
        """

    def user_is_invisible(self, user_id):
        """

        :param user_id:
        :return:
        """

    def set_user_offline(self, user_id: str) -> None:
        """

        :param user_id:
        :return:
        """

    def set_user_online(self, user_id: str) -> None:
        """

        :param user_id:
        :return:
        """

    def set_user_invisible(self, user_id: str) -> None:
        """

        :param user_id:
        :return:
        """
