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
from activitystreams.models.activity import Activity


class IStorage(Interface):
    def store_message(self, activity: Activity) -> None:
        """
        save this message to the storage

        :param activity: the activity to store
        :return: nothing
        """

    def get_all_message_ids_for_user(self, user_id: str):
        """
        get all message ids, even for soft-deleted messages

        :param user_id:
        :return:
        """

    def get_message(self, message_id: str) -> dict:
        """
        get the message with the given ID

        :param message_id: uuid of the message
        :return: a dict describing the message
        """

    def get_statuses(self, message_ids: set, receiver_id: str) -> dict:
        """
        get the ack statuses for a set of messages sent to one specific user

        :param message_ids: set of message ids
        :param receiver_id: the id of the receiver user/room
        :return: a dict of {msg_id: ack_status} for this user
        """

    def mark_as_received(self, message_ids: set, receiver_id: str) -> None:
        """
        mark messages as received by client

        :param message_ids: a set of message uuids
        :param receiver_id: the uuid of the receiving user, must match for update to be done
        :return: nothing
        """

    def mark_as_read(self, message_ids: set, receiver_id: str, target_id: str) -> None:
        """
        mark messages as read by client

        :param message_ids: a set of message uuids
        :param receiver_id: the uuid of the receiving user, must match for update to be done
        :param target_id: the uuid of the room the message is in
        :return: nothing
        """

    def get_messages(self, message_ids: set) -> list:
        """
        get all messages with the given IDs

        :param message_ids: set of uuids of messages
        :return: a list of dicts describing the messages
        """

    def get_history(self, room_id: str, limit: int = 100) -> list:
        """
        get history for a room

        :param room_id: the room uuid
        :param limit: optional limit, default is 100 latest messages
        :return: a list of messages
        """

    def get_unread_history(self, room_id: str, time_stamp: int, limit: int = 100) -> list:
        """
        get unread history after a certain timestamp for a room

        :param room_id: the uuid of the room
        :param time_stamp: the last read timestamp, get everything after this
        :param limit: optional limit, if None, a limit of 100 will be set
        :return: a list of messages
        """

    def delete_message(self, message_id: str, room_id: str=None) -> None:
        """
        delete a message

        :param message_id: the uuid of the message to delete
        :return: nothing
        """
