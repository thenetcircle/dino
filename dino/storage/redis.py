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
from uuid import uuid4 as uuid

from dino.storage import IStorage
from dino import environ
from dino.config import ConfigKeys
from dino.config import SessionKeys
from dino.config import RedisKeys

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


@implementer(IStorage)
class StorageRedis(object):
    redis = None

    def __init__(self, host: str, port: int = 6379, db: int = 0):
        if environ.env.config.get(ConfigKeys.TESTING, False) or host == 'mock':
            from fakeredis import FakeStrictRedis as Redis
        else:
            from redis import Redis

        self.redis = Redis(host=host, port=port, db=db)

    def store_message(self, activity: Activity) -> None:
        target = activity.target.id
        user_name = environ.env.session.get(SessionKeys.user_name.value)
        msg = activity.object.content

        self.redis.lpush(
                RedisKeys.room_history(target),
                '%s,%s,%s,%s' % (activity.id, activity.published, user_name, msg))

        max_history = environ.env.config.get(ConfigKeys.MAX_HISTORY, -1)
        if max_history > 0:
            self.redis.ltrim(RedisKeys.room_history(target), 0, max_history)

    def delete_message(self, room_id: str, message_id: str):
        if message_id is None or message_id == '':
            return

        all_history = self.redis.lrange(RedisKeys.room_history(room_id), 0, -1)
        found_msg = None
        for history in all_history:
            if str(history, 'utf-8').startswith(message_id):
                found_msg = history
                break

        self.redis.lrem(RedisKeys.room_history(room_id), found_msg, 1)

    def create_room(self, activity: Activity) -> None:
        room_name = activity.target.display_name
        room_id = activity.target.id

        self.redis.set(RedisKeys.room_name_for_id(room_id), room_name)
        self.redis.hset(RedisKeys.room_owners(room_id), activity.actor.id,
                        environ.env.session.get(SessionKeys.user_name.value))
        self.redis.hset(RedisKeys.rooms(), room_id, room_name)

    def get_history(self, room_id: str, limit: int = None):
        if limit is None:
            limit = -1

        messages = self.redis.lrange(RedisKeys.room_history(room_id), 0, limit)

        cleaned_messages = list()
        for message_entry in messages:
            message_entry = str(message_entry, 'utf-8')
            cleaned_messages.append(message_entry.split(',', 3))

        return cleaned_messages

    def set_user_offline(self, user_id: str) -> None:
        self.redis.setbit(RedisKeys.online_bitmap(), int(user_id), 0)
        self.redis.srem(RedisKeys.online_set(), int(user_id))
        self.redis.srem(RedisKeys.users_multi_cast(), user_id)
        self.redis.set(RedisKeys.user_status(user_id), RedisKeys.REDIS_STATUS_UNAVAILABLE)

    def set_user_online(self, user_id: str) -> None:
        self.redis.setbit(RedisKeys.online_bitmap(), int(user_id), 1)
        self.redis.sadd(RedisKeys.online_set(), int(user_id))
        self.redis.sadd(RedisKeys.users_multi_cast(), user_id)
        self.redis.set(RedisKeys.user_status(user_id), RedisKeys.REDIS_STATUS_AVAILABLE)

    def set_user_invisible(self, user_id: str) -> None:
        self.redis.setbit(RedisKeys.online_bitmap(), int(user_id), 0)
        self.redis.srem(RedisKeys.online_set(), int(user_id))
        self.redis.sadd(RedisKeys.users_multi_cast(), user_id)
        self.redis.set(RedisKeys.user_status(user_id), RedisKeys.REDIS_STATUS_INVISIBLE)

    def get_room_name(self, room_id: str) -> str:
        room_name = self.redis.get(RedisKeys.room_name_for_id(room_id))
        if room_name is None:
            room_name = str(uuid())
            environ.env.logger.warn(
                'WARN: room_name for room_id %s is None, generated new name: %s' % (room_id, room_name))
            self.redis.set(RedisKeys.room_name_for_id(room_id), room_name)
        else:
            room_name = room_name.decode('utf-8')
        return room_name

    def join_room(self, user_id: str, user_name: str, room_id: str, room_name: str) -> None:
        self.redis.sadd(RedisKeys.rooms_for_user(user_id), '%s:%s' % (room_id, room_name))
        self.redis.hset(RedisKeys.users_in_room(room_id), user_id, user_name)
        self.redis.hset(RedisKeys.rooms(), room_id, room_name)

    def users_in_room(self, room_id: str) -> list:
        users = self.redis.hgetall(RedisKeys.users_in_room(room_id))
        cleaned_users = list()
        for user_id, user_name in users.items():
            cleaned_users.append((
                str(user_id, 'utf-8'),
                str(user_name, 'utf-8')
            ))
        return cleaned_users

    def get_all_rooms(self, user_id: str = None) -> dict:
        clean_rooms = list()

        if user_id is None:
            rooms = self.redis.hgetall(RedisKeys.rooms())
            for room_id, room_name in rooms.items():
                clean_rooms.append({
                    'room_id': str(room_id, 'utf-8'),
                    'room_name': str(room_name, 'utf-8'),
                })

        else:
            rooms = self.redis.smembers(RedisKeys.rooms_for_user(user_id))
            for room in rooms:
                room_id, room_name = str(room, 'utf-8').split(':', 1)
                clean_rooms.append({
                    'room_id': room_id,
                    'room_name': room_name,
                })

        return clean_rooms

    def leave_room(self, user_id: str, room_id: str) -> None:
        self.redis.hdel(RedisKeys.users_in_room(room_id), user_id)
        self.redis.srem(RedisKeys.rooms_for_user(user_id), room_id)

    def room_exists(self, room_id: str) -> bool:
        return self.redis.hexists(RedisKeys.rooms(), room_id)

    def room_name_exists(self, room_name: str) -> bool:
        cleaned = set()
        for room_name in self.redis.hvals(RedisKeys.rooms()):
            cleaned.add(str(room_name, 'utf-8').lower())

        if type(room_name) == bytes:
            room_name = str(room_name, 'utf-8')

        return room_name.lower() in cleaned

    def room_contains(self, room_id: str, user_id: str) -> bool:
        return self.redis.hexists(RedisKeys.users_in_room(room_id), user_id)

    def get_owners(self, room_id: str) -> dict:
        owners = self.redis.hgetall(RedisKeys.room_owners(room_id))

        cleaned = dict()
        for user_id, user_name in owners.items():
            cleaned[str(user_id, 'utf-8')] = str(user_name, 'utf-8')

        return cleaned

    def room_owners_contain(self, room_id: str, user_id: str) -> bool:
        return self.redis.hexists(RedisKeys.room_owners(room_id), user_id)
