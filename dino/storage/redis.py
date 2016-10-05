from zope.interface import implementer
from activitystreams.models.activity import Activity
from uuid import uuid4 as uuid

from dino.storage.base import IStorage
from dino.env import env
from dino.env import SessionKeys
from dino.env import ConfigKeys

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class RedisKeys(object):
    RKEY_ROOMS_FOR_USER = 'user:rooms:%s'  # user:rooms:user_id
    RKEY_USERS_IN_ROOM = 'room:%s'  # room:room_id
    RKEY_ROOMS = 'rooms'
    RKEY_ONLINE_BITMAP = 'users:online:bitmap'
    RKEY_ONLINE_SET = 'users:online:set'
    RKEY_MULTI_CAST = 'users:multicat'
    RKEY_USER_STATUS = 'user:status:%s'  # user:status:user_id
    RKEY_ROOM_NAME = 'room:name:%s'  # room:name:room_id
    RKEY_ROOM_ACL = 'room:acl:%s'  # room:acl:room_id
    RKEY_ROOM_OWNERS = 'room:owners:%s'  # room:owners:room_id
    RKEY_ROOM_HISTORY = 'room:history:%s'  # room:history:room_id

    REDIS_STATUS_AVAILABLE = '1'
    # REDIS_STATUS_CHAT = '2'
    REDIS_STATUS_INVISIBLE = '3'
    REDIS_STATUS_UNAVAILABLE = '4'
    # REDIS_STATUS_UNKNOWN = '5'

    @staticmethod
    def rooms_for_user(user_id: str) -> str:
        return RedisKeys.RKEY_ROOMS_FOR_USER % user_id

    @staticmethod
    def users_in_room(room_id: str) -> str:
        return RedisKeys.RKEY_USERS_IN_ROOM % room_id

    @staticmethod
    def rooms() -> str:
        return RedisKeys.RKEY_ROOMS

    @staticmethod
    def room_name_for_id(room_id: str) -> str:
        return RedisKeys.RKEY_ROOM_NAME % room_id

    @staticmethod
    def online_bitmap() -> str:
        return RedisKeys.RKEY_ONLINE_BITMAP

    @staticmethod
    def online_set() -> str:
        return RedisKeys.RKEY_ONLINE_SET

    @staticmethod
    def users_multi_cast() -> str:
        return RedisKeys.RKEY_MULTI_CAST

    @staticmethod
    def user_status(user_id: str) -> str:
        return RedisKeys.RKEY_USER_STATUS % user_id

    @staticmethod
    def room_history(room_id: str) -> str:
        return RedisKeys.RKEY_ROOM_HISTORY % room_id

    @staticmethod
    def room_acl(room_id: str) -> dict:
        return RedisKeys.RKEY_ROOM_ACL % room_id

    @staticmethod
    def room_owners(room_id: str) -> str:
        return RedisKeys.RKEY_ROOM_OWNERS % room_id


@implementer(IStorage)
class RedisStorage(object):
    redis = None

    def __init__(self, host: str, port: int=6379):
        if env.config.get(ConfigKeys.TESTING, False):
            from fakeredis import FakeStrictRedis as Redis
        else:
            from redis import Redis

        self.redis = Redis(host=host, port=port)

    def store_message(self, activity: Activity) -> None:
        target = activity.target.id
        user_name = env.session.get(SessionKeys.user_name.value)
        msg = activity.object.content

        self.redis.lpush(
                RedisKeys.room_history(target),
                '%s,%s,%s,%s' % (activity.id, activity.published, user_name, msg))

        max_history = env.config.get(ConfigKeys.MAX_HISTORY, -1)
        if max_history > 0:
            self.redis.ltrim(RedisKeys.room_history(target), 0, max_history)

    def create_room(self, activity: Activity) -> None:
        room_name = activity.target.display_name
        room_id = activity.target.id

        self.redis.set(RedisKeys.room_name_for_id(room_id), room_name)
        self.redis.hset(RedisKeys.room_owners(room_id), activity.actor.id, env.session.get(SessionKeys.user_name.value))
        self.redis.hset(RedisKeys.rooms(), room_id, room_name)

    def delete_acl(self, room_id: str, acl_type: str) -> None:
        self.redis.hdel(RedisKeys.room_acl(room_id), acl_type)

    def add_acls(self, room_id: str, acls: dict) -> None:
        self.redis.hmset(RedisKeys.room_acl(room_id), acls)

    def get_acls(self, room_id: str) -> list:
        acls = self.redis.hgetall(RedisKeys.room_acl(room_id))
        acls_cleaned = dict()

        for acl_type, acl_value in acls.items():
            acls_cleaned[str(acl_type, 'utf-8')] = str(acl_value, 'utf-8')

        return acls_cleaned

    def get_history(self, room_id: str, limit: int=None):
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
            env.logger.warn('WARN: room_name for room_id %s is None, generated new name: %s' % (room_id, room_name))
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
                str(user_id.decode('utf-8')),
                str(user_name.decode('utf-8'))
            ))
        return cleaned_users

    def get_all_rooms(self, user_id: str=None) -> dict:
        if user_id is None:
            return self.redis.hgetall(RedisKeys.rooms())
        return self.redis.smembers(RedisKeys.rooms_for_user(user_id))

    def leave_room(self, user_id: str, room_id: str) -> None:
        self.redis.hdel(RedisKeys.users_in_room(room_id), user_id)
        self.redis.srem(RedisKeys.rooms_for_user(user_id), room_id)

    def remove_current_rooms_for_user(self, user_id: str) -> None:
        self.redis.delete(RedisKeys.rooms_for_user(user_id))

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
