#!/usr/bin/env python

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

from typing import Union
from zope.interface import implementer

from dino import environ
from dino.config import SessionKeys
from dino.config import ConfigKeys
from dino.config import RedisKeys
from dino.auth.base import IAuth

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


@implementer(IAuth)
class AuthRedis(object):
    def __init__(self, host: str, port: int = 6379, db: int = 0):
        if environ.env.config.get(ConfigKeys.TESTING, False) or host == 'mock':
            from fakeredis import FakeStrictRedis as Redis
        else:
            from redis import Redis

        self.redis = Redis(host=host, port=port, db=db)

    def authenticate_and_populate_session(self, user_id: str, token: str) -> (bool, Union[None, str], Union[None, dict]):
        if user_id is None or len(user_id) == 0:
            return False, 'no user_id supplied', None
        if token is None or len(token) == 0:
            return False, 'no token supplied', None

        key = RedisKeys.auth_key(user_id)
        stored_session = self.redis.hgetall(key)

        if stored_session is None or len(stored_session) == 0:
            return False, 'no session found for this user id, not logged in yet', None

        stored_token = stored_session.get(SessionKeys.token.value)
        supplied_token = stored_session.get(SessionKeys.token.value)

        if stored_token != supplied_token:
            environ.env.logger.warning('user "%s" supplied token "%s" but stored token is "%s"' %
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
