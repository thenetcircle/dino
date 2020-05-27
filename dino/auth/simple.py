import fakeredis
from typing import Union

from dino.auth import IAuth


class AllowAllAuth(IAuth):
    def __init__(self):
        self.redis = fakeredis.FakeStrictRedis()

    def get_user_info(self, user_id: str) -> dict:
        return dict()

    def authenticate_and_populate_session(self, user_id: str, token: str) -> (bool, Union[None, str], Union[None, dict]):
        return True, None, {'user_id': user_id, 'token': token, 'user_name': 'user_name'}
    
    def update_session_for_key(self, user_id: str, session_key: str, session_value: str) -> None:
        pass


class DenyAllAuth(IAuth):
    def __init__(self):
        self.redis = fakeredis.FakeStrictRedis()

    def get_user_info(self, user_id: str) -> dict:
        return dict()

    def authenticate_and_populate_session(self, user_id: str, token: str) -> (bool, Union[None, str], Union[None, dict]):
        return False, 'not allowed', None
