from zope.interface import Interface
from activitystreams.models.activity import Activity


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
