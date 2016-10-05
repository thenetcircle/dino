from zope.interface import Interface
from activitystreams.models.activity import Activity


class IStorage(Interface):
    def save_message(self, activity: Activity) -> None:
        """
        save this message to the storage

        :param activity: the activity to store
        :return: nothing
        """
