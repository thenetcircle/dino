from zope.interface import Interface
from activitystreams.models.activity import Activity
from cassandra.cluster import ResultSet


class IStorage(Interface):
    def store_message(self, activity: Activity) -> None:
        """
        save this message to the storage

        :param activity: the activity to store
        :return: nothing
        """

    def get_history(self, room_id: str, limit: int = None) -> list:
        """

        :param room_id:
        :param limit:
        :return:
        """

    def delete_message(self, message_id: str) -> None:
        """

        :param message_id:
        :return:
        """


class IDriver(Interface):
    def init(self):
        """
        creates keyspace, tables, views etc.

        :return: nothing
        """

    def msg_select(self, msg_id) -> ResultSet:
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

    def msgs_select(self, to_user_id: str) -> ResultSet:
        """
        find all messages sent to a user id/room id

        :param to_user_id: either a user id or room uuid
        :return: all messages to this user/room
        """
