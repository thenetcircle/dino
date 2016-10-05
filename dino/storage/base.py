from zope.interface import Interface
from activitystreams.models.activity import Activity


class IStorage(Interface):
    def save_message(self, activity: Activity) -> None:
        """
        save this message to the storage

        :param activity: the activity to store
        :return: nothing
        """

    def create_room(self, activity: Activity) -> None:
        """

        :param activity:
        :return:
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

    def get_history(self, room_id: str, limit: int=None):
        """

        :param room_id:
        :param limit:
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

    def get_room_name(self, room_id: str) -> str:
        """

        :param room_id:
        :return:
        """

    def join_room(self, user_id: str, user_name: str, room_id: str, room_name: str) -> None:
        """

        :param user_id:
        :param user_name:
        :param room_id:
        :param room_name:
        :return:
        """

    def users_in_room(self, room_id: str) -> list:
        """

        :param room_id:
        :return:
        """

    def get_all_rooms(self, user_id: str=None) -> dict:
        """

        :param user_id:
        :return:
        """

    def leave_room(self, user_id: str, room_id: str) -> None:
        """

        :param user_id:
        :param room_id:
        :return:
        """

    def remove_current_rooms_for_user(self, user_id: str) -> None:
        """

        :param user_id:
        :return:
        """

    def room_exists(self, room_id: str) -> bool:
        """

        :param room_id:
        :return:
        """

    def room_name_exists(self, room_name: str) -> bool:
        """

        :param room_name:
        :return:
        """

    def room_contains(self, room_id: str, user_id: str) -> bool:
        """

        :param room_id:
        :param user_id:
        :return:
        """

    def get_owners(self, room_id: str) -> dict:
        """

        :param room_id:
        :return:
        """

    def room_owners_contain(self, room_id: str, user_id: str) -> bool:
        """

        :param room_id:
        :param user_id:
        :return:
        """