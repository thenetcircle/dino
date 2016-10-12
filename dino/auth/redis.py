from typing import Union

from dino.env import SessionKeys
from dino.env import ConfigKeys
from dino.env import env
from dino import rkeys

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class AuthRedis(object):
    DEFAULT_AUTH_KEY = 'user:auth:%s'

    def __init__(self, host: str, port: int=6379, db: int=0):
        if env.config.get(ConfigKeys.TESTING, False):
            from fakeredis import FakeStrictRedis as Redis
        else:
            from redis import Redis

        self.redis = Redis(host=host, port=port, db=db)

    def authenticate_and_populate_session(self, user_id: str, token: str) -> (bool, Union[None, str], Union[None, dict]):
        if user_id is None or len(user_id) == 0:
            return False, 'no user_id supplied', None
        if token is None or len(token) == 0:
            return False, 'no token supplied', None

        key = env.config.get(ConfigKeys.REDIS_AUTH_KEY, None)
        if key is None:
            key = rkeys.auth_key(user_id)
        else:
            key %= user_id

        stored_session = self.redis.hgetall(key)

        if stored_session is None or len(stored_session) == 0:
            return False, 'no session found for this user id, not logged in yet', None

        stored_token = stored_session.get(SessionKeys.token.value)
        supplied_token = stored_session.get(SessionKeys.token.value)

        if stored_token != supplied_token:
            env.logger.warning('user "%s" supplied token "%s" but stored token is "%s"' %
                               (user_id, supplied_token, stored_token))
            return False, 'invalid token "%s" supplied for user id "%s"' % (supplied_token, user_id), None

        cleaned_session = dict()
        for stored_key, stored_value in stored_session.items():
            cleaned_session[str(stored_key, 'utf-8')] = str(stored_value, 'utf-8')

        session = dict()
        for session_key in SessionKeys:
            if not isinstance(session_key.value, str):
                continue

            session_value = cleaned_session.get(session_key.value)
            if session_value is None or not isinstance(session_value, str) or len(session_value) == 0:
                continue
            session[session_key.value] = session_value

        return True, None, session
