import logging
import traceback
import redis
from typing import Union

from dino.auth import IAuth
from dino.config import ConfigKeys
from dino.config import RedisKeys
from dino.config import SessionKeys

logger = logging.getLogger()


class AuthRedis(IAuth):
    def __init__(self, host: str, port: int = 6379, db: int = 0, env=None):
        if env.config.get(ConfigKeys.TESTING, False) or host == 'mock':
            from fakeredis import FakeStrictRedis

            self.redis_pool = None
            self.redis_instance = FakeStrictRedis(host=host, port=port, db=db)
        else:
            self.redis_pool = redis.ConnectionPool(host=host, port=port, db=db)
            self.redis_instance = None

        if env is None:
            from dino import environ
            self.env = environ.env
        else:
            self.env = env

    @property
    def redis(self):
        if self.redis_pool is None:
            return self.redis_instance
        return redis.Redis(connection_pool=self.redis_pool)

    def get_user_info(self, user_id: str) -> dict:
        key = RedisKeys.auth_key(user_id)
        session = self.env.cache.get_user_info(user_id)
        if session is not None:
            return session

        binary_stored_session = self.redis.hgetall(key)
        stored_session = dict()

        for key, val in binary_stored_session.items():
            if type(key) == bytes:
                key = str(key, 'utf-8')
            if type(val) == bytes:
                val = str(val, 'utf-8')

            if key in [SessionKeys.token.value, SessionKeys.user_name.value, SessionKeys.user_id.value]:
                continue
            stored_session[key] = val

        self.env.cache.set_user_info(user_id, stored_session)
        return stored_session

    def update_session_for_key(self, user_id: str, session_key: str, session_value: str) -> None:
        key = RedisKeys.auth_key(user_id)
        try:
            self.redis.hset(key, session_key, session_value)
        except Exception as e:
            logger.error(
                    'could not update session for user %s; key "%s", value "%s": %s',
                    user_id, session_key, session_value, str(e))
            logger.exception(traceback.format_exc(e))

    def authenticate_and_populate_session(self, user_id: str, supplied_token: str) -> (bool, Union[None, str], Union[None, dict]):
        if user_id is None or len(user_id) == 0:
            return False, 'no user_id supplied', None
        if supplied_token is None or len(supplied_token) == 0:
            return False, 'no token supplied', None

        key = RedisKeys.auth_key(user_id)
        binary_stored_session = self.redis.hgetall(key)
        stored_session = dict()

        for key, val in binary_stored_session.items():
            if type(key) == bytes:
                key = str(key, 'utf-8')
            if type(val) == bytes:
                val = str(val, 'utf-8')
            stored_session[key] = val

        if stored_session is None or len(stored_session) == 0:
            return False, 'no session found for this user id, not logged in yet', None

        stored_token = stored_session.get(SessionKeys.token.value)
        if stored_token != supplied_token:
            logger.warning(
                'user "%s" supplied token "%s" but stored token is "%s"' % (user_id, supplied_token, stored_token))
            return False, 'invalid token "%s" supplied for user id "%s"' % (supplied_token, user_id), None

        session = dict()
        for session_key in SessionKeys:
            if not isinstance(session_key.value, str):
                continue

            session_value = stored_session.get(session_key.value)
            if session_value is None or not isinstance(session_value, str) or len(session_value) == 0:
                continue
            session[session_key.value] = session_value

        return True, None, session
