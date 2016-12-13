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

from zope.interface import implementer
from activitystreams.models.activity import Activity

from dino import environ
from dino.storage import IStorage
from dino.config import ConfigKeys
from dino.config import SessionKeys
from dino.config import RedisKeys
from dino.utils import is_base64
from dino.utils import b64d
from dino.utils import b64e

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


@implementer(IStorage)
class StorageRedis(object):
    redis = None

    def __init__(self, host: str, port: int = 6379, db: int = 0):
        if environ.env.config.get(ConfigKeys.TESTING, False) or host == 'mock':
            from fakeredis import FakeRedis as Redis
        else:
            from redis import Redis

        self.redis = Redis(host=host, port=port, db=db)

    def store_message(self, activity: Activity) -> None:
        target = activity.target.id
        user_id = environ.env.session.get(SessionKeys.user_id.value)
        user_name = b64e(environ.env.session.get(SessionKeys.user_name.value))
        msg = activity.object.content

        if not is_base64(msg):
            raise RuntimeError('message is not base64')

        self.redis.lpush(
                RedisKeys.room_history(target),
                '%s,%s,%s,%s,%s' % (activity.id, activity.published, user_id, user_name, msg))

        max_history = environ.env.config.get(ConfigKeys.LIMIT, domain=ConfigKeys.HISTORY, default=-1)
        if max_history > 0:
            self.redis.ltrim(RedisKeys.room_history(target), 0, max_history)

    def delete_message(self, room_id: str, message_id: str):
        if message_id is None or message_id == '':
            return

        all_history = self.redis.lrange(RedisKeys.room_history(room_id), 0, -1)
        found_msg = None
        for history in all_history:
            history = str(history, 'utf-8')
            if history.startswith(message_id):
                found_msg = history
                break

        self.redis.lrem(RedisKeys.room_history(room_id), found_msg, 1)

    def get_history(self, room_id: str, limit: int = 100):
        if limit is None:
            limit = -1

        messages = self.redis.lrange(RedisKeys.room_history(room_id), 0, limit)

        cleaned_messages = list()
        for message_entry in messages:
            message_entry = str(message_entry, 'utf-8')
            msg_id, published, user_id, user_name, msg = message_entry.split(',', 4)
            cleaned_messages.append({
                'message_id': msg_id,
                'from_user': user_id,
                'to_user': room_id,
                'body': b64d(msg),
                'domain': 'room',
                'channel_id': '',
                'timestamp': published,
                'deleted': False
            })

        return cleaned_messages

    def get_unread_history(self, room_id: str, time_stamp: int, limit: int = 100) -> list:
        raise NotImplementedError()
