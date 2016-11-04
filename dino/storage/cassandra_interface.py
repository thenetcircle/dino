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


class IDriver(Interface):
    def init(self):
        """
        creates keyspace, tables, views etc.

        :return: nothing
        """

    def msg_select(self, msg_id):
        """
        select one message

        :param msg_id: uuid of the message
        :return: the message, if found
        """

    def msg_insert(self, msg_id, from_user, to_user, body, domain, timestamp, channel_id, deleted=False) -> None:
        """
        store a new message

        :param msg_id: uuid of the message
        :param from_user: id of the user sending the message
        :param to_user: id of the user receiving the message (or uuid of the target room)
        :param body: the message text
        :param domain: private/group
        :param timestamp: published timestamp
        :param channel_id: the channel of the room
        :param deleted: if the message is deleted or not
        :return: nothing
        """

    def msgs_select(self, to_user_id: str):
        """
        find all messages sent to a user id/room id

        :param to_user_id: either a user id or room uuid
        :return: all messages to this user/room
        """
