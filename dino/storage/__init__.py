from zope.interface import Interface
from activitystreams.models.activity import Activity


class IStorage(Interface):
    def store_message(self, activity: Activity) -> None:
        """
        save this message to the storage

        :param activity: the activity to store
        :return: nothing
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

    def delete_message(self, message_id: str) -> None:
        """
        delete a message

        :param message_id: the uuid of the message to delete
        :return: nothing
        """
