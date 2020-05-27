from abc import ABC
from typing import Union


class IAuth(ABC):
    def authenticate_and_populate_session(self, user_id: str, token: str) -> (bool, Union[None, str], Union[None, dict]):
        """
        authenticates a user with a token

        :param user_id: the user id
        :param token: the token for the login
        :return: if success: (True, None, <dict with session values>), if failure: (False, <error string>, None)
        """

    def get_user_info(self, user_id: str) -> dict:
        """
        get the information about a user stored for validation purposes for acls, e.g. age, gender etc.

        token, user_id and user_name will be skipped (if present)

        :param user_id: the id of the user
        :return: a dict with user info
        """
