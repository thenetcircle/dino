import json
import logging
import traceback
import random
import sys
import socket

from zope.interface import implementer
from typing import Union, List
from typing import Dict
from typing import Tuple

from dino.config import RedisKeys
from dino.config import ConfigKeys
from dino.config import UserKeys
from dino.config import RoleKeys
from dino.cache import ICache
from datetime import datetime
from datetime import timedelta
import redis

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

EIGHT_HOURS_IN_SECONDS = 8*60*60
TEN_MINUTES = 10*60
FIVE_MINUTES = 5*60
ONE_MINUTE = 60
THIRTY_SECONDS = 30
ONE_HOUR = 60*60
TEN_SECONDS = 10

logger = logging.getLogger(__name__)


class MemoryCache(object):
    def __init__(self):
        self.vals = dict()

    def set(self, key, value, ttl=30):
        try:
            expires_at = (datetime.utcnow() + timedelta(seconds=ttl)).timestamp()
            self.vals[key] = (expires_at, value)
        except:
            pass

    def get(self, key):
        try:
            if key not in self.vals:
                return None
            expires_at, value = self.vals[key]
            now = datetime.utcnow().timestamp()
            if now > expires_at:
                del self.vals[key]
                return None
            return value
        except:
            return None

    def delete(self, key):
        if key in self.vals:
            del self.vals[key]

    def flushall(self):
        self.vals = dict()


@implementer(ICache)
class CacheRedis(object):
    def __init__(self, env, host: str, port: int = 6379, db: int = 0):
        if env.config.get(ConfigKeys.TESTING, False) or host == 'mock':
            from fakeredis import FakeStrictRedis

            self.redis_pool = None
            self.redis_instance = FakeStrictRedis(host=host, port=port, db=db)
        else:
            self.redis_pool = redis.ConnectionPool(host=host, port=port, db=db)
            self.redis_instance = None

        self.cache = MemoryCache()

        args = sys.argv
        for a in ['--bind', '-b']:
            bind_arg_pos = [i for i, x in enumerate(args) if x == a]
            if len(bind_arg_pos) > 0:
                bind_arg_pos = bind_arg_pos[0]
                break

        self.listen_port = 'standalone'
        if bind_arg_pos is not None and not isinstance(bind_arg_pos, list):
            self.listen_port = args[bind_arg_pos + 1].split(':')[1]

        self.listen_host = socket.gethostname().split('.')[0]

    @property
    def redis(self):
        if self.redis_pool is None:
            return self.redis_instance
        return redis.Redis(connection_pool=self.redis_pool)

    def _flushall(self) -> None:
        self.redis.flushdb()
        self.cache.flushall()

    def _set(self, key, val, ttl=None) -> None:
        if ttl is None:
            self.cache.set(key, val)
        else:
            self.cache.set(key, val, ttl=ttl)

    def _get(self, key):
        return self.cache.get(key)

    def _del(self, key) -> None:
        self.cache.delete(key)

    def get_all_permanent_rooms(self):
        key = RedisKeys.all_permanent_rooms()
        rooms = self.redis.get(key)
        if rooms is None or len(rooms) == 0:
            return None

        return str(rooms, 'utf-8').split(',')

    def set_all_permanent_rooms(self, rooms):
        rooms_str = ','.join(rooms)
        key = RedisKeys.all_permanent_rooms()
        self.redis.set(key, rooms_str)
        self.redis.expire(key, FIVE_MINUTES)

    def get_room_acls_for_action(self, action: str) -> Union[None, Dict[str, Dict[str, str]]]:
        key = RedisKeys.rooms_with_action(action)
        room_ids_bytes = self.redis.get(key)

        if room_ids_bytes is None:
            return None

        room_ids_str = str(room_ids_bytes, 'utf-8')
        room_ids = room_ids_str.split(',')

        if len(room_ids) == 0:
            return None

        room_acls = dict()
        for room_id in room_ids:
            key = RedisKeys.room_acls_for_action(room_id, action)
            acls = self.redis.hgetall(key)

            str_acls = dict()
            for acl_type, acl_value in acls.items():
                str_acls[str(acl_type, 'utf-8')] = str(acl_value, 'utf-8')

            room_acls[room_id] = str_acls

        return room_acls

    def set_room_acls_for_action(self, action: str, acls: Dict[str, Dict[str, str]]) -> None:
        for room_id, values in acls.items():
            key = RedisKeys.room_acls_for_action(room_id, action)
            self.redis.hmset(key, values)
            self.redis.expire(key, TEN_MINUTES)

        room_ids = list(acls.keys())
        key = RedisKeys.rooms_with_action(action)

        # avoid race condition that could happen if we used lists instead; after clearing a
        # list and before filling it with this updated list of room ids, another client
        # might be querying redis and getting 0 results
        room_ids_str = ','.join(room_ids)
        self.redis.set(key, room_ids_str)
        self.redis.expire(key, TEN_MINUTES)

    def add_heartbeat(self, user_id: str) -> None:
        redis_key = RedisKeys.heartbeat_user(user_id)
        self.redis.set(redis_key, user_id)
        self.redis.expire(redis_key, ONE_MINUTE)

    def check_heartbeat(self, user_id: str) -> bool:
        exists = self.has_heartbeat(user_id)
        if exists:
            self.add_heartbeat(user_id)  # will reset the ttl
        return exists

    def has_heartbeat(self, user_id: str) -> bool:
        redis_key = RedisKeys.heartbeat_user(user_id)
        return self.redis.exists(redis_key)

    def get_rooms_for_user(self, user_id: str):
        clean_rooms = dict()

        rooms = self.redis.hgetall(RedisKeys.rooms_for_user(user_id))
        if rooms is None or len(rooms) == 0:
            return clean_rooms

        for room_id, room_name in rooms.items():
            room_id, room_name = str(room_id, 'utf-8'), str(room_name, 'utf-8')
            clean_rooms[room_id] = room_name
        return clean_rooms

    def set_rooms_for_user(self, user_id: str, rooms: dict):
        """
        set the room uuids the user is in

        :param user_id: the uuid of the user
        :param rooms: a dict of rooms the user is in now {room_uuid: room_name}
        :return: nothing
        """
        redis_key = RedisKeys.rooms_for_user(user_id)

        if rooms is None or len(rooms) == 0:
            self.redis.delete(redis_key)
        else:
            self.redis.hmset(redis_key, rooms)
            self.redis.expire(redis_key, int(2*TEN_SECONDS + random.random()*TEN_SECONDS))

    def remove_rooms_for_user(self, user_id: str) -> None:
        redis_key = RedisKeys.rooms_for_user(user_id)
        self.redis.delete(redis_key)

    def leave_room_for_user(self, user_id: str, room_id: str) -> None:
        redis_key = RedisKeys.rooms_for_user(user_id)
        self.redis.hdel(redis_key, room_id)

    def is_user_in_room(self, user_id: str, room_id: str):
        return self.redis.hexists(RedisKeys.rooms_for_user(user_id), room_id)

    def set_user_in_room(self, user_id: str, room_id: str, room_name: str):
        return self.redis.hset(RedisKeys.rooms_for_user(user_id), room_id, room_name)

    def set_type_of_rooms_in_channel(self, channel_id: str, object_type: str) -> None:
        cache_key = RedisKeys.room_types_in_channel(channel_id)
        self.cache.set(cache_key, object_type, ttl=ONE_MINUTE + random.random()*ONE_MINUTE)

    def get_type_of_rooms_in_channel(self, channel_id: str) -> str:
        cache_key = RedisKeys.room_types_in_channel(channel_id)
        return self.cache.get(cache_key)

    def set_is_room_ephemeral(self, room_id: str, is_ephemeral: bool) -> None:
        redis_key = RedisKeys.non_ephemeral_rooms()
        cache_key = '%s-%s' % (redis_key, room_id)
        self.cache.set(cache_key, is_ephemeral)

    def is_room_ephemeral(self, room_id: str) -> bool:
        redis_key = RedisKeys.non_ephemeral_rooms()
        cache_key = '%s-%s' % (redis_key, room_id)
        return self.cache.get(cache_key)

    def set_default_rooms(self, rooms: list) -> None:
        cache_key = RedisKeys.default_rooms()
        self.cache.set(cache_key, rooms, ttl=FIVE_MINUTES)

    def clear_default_rooms(self) -> None:
        redis_key = RedisKeys.default_rooms()
        self.cache.delete(redis_key)

    def get_default_rooms(self) -> list:
        redis_key = RedisKeys.default_rooms()
        value = self.cache.get(redis_key)
        if value is not None:
            return value

        rooms = self.redis.smembers(redis_key)
        if rooms is not None and len(rooms) > 0:
            rooms = [str(room, 'utf-8') for room in rooms]
            self.cache.set(redis_key, rooms, ttl=FIVE_MINUTES)
            return rooms
        return None

    def get_black_list(self) -> set:
        cache_key = RedisKeys.black_list()
        value = self.cache.get(cache_key)
        if value is not None:
            return value

        values = self.redis.smembers(cache_key)
        if value is not None:
            decoded = {str(v, 'utf-8') for v in values}
            self.cache.set(cache_key, decoded, ttl=TEN_MINUTES)
            return decoded
        return None

    def reset_black_list(self) -> None:
        cache_key = RedisKeys.black_list()
        self.cache.delete(cache_key)
        self.redis.delete(cache_key)

    def set_black_list(self, the_list: set) -> None:
        cache_key = RedisKeys.black_list()
        self.cache.set(cache_key, the_list, ttl=TEN_MINUTES)
        self.redis.delete(cache_key)
        self.redis.sadd(cache_key, *the_list)

    def remove_from_black_list(self, word: str) -> None:
        cache_key = RedisKeys.black_list()
        the_cached_list = self.cache.get(cache_key)
        the_cached_list.remove(word)
        self.cache.set(cache_key, the_cached_list, ttl=60*10)
        self.redis.srem(cache_key, word)

    def add_to_black_list(self, word: str) -> None:
        cache_key = RedisKeys.black_list()
        the_cached_list = self.cache.get(cache_key)
        the_cached_list.add(word)
        self.cache.set(cache_key, the_cached_list, ttl=60*10)
        self.redis.sadd(cache_key, word)

    def _set_ban_timestamp(self, key: str, user_id: str, timestamp: str) -> None:
        cache_key = '%s-%s' % (key, user_id)
        self.cache.set(cache_key, timestamp)
        self.redis.hset(key, user_id, timestamp)

    def set_global_ban_timestamp(self, user_id: str, duration: str, timestamp: str, username: str) -> None:
        key = RedisKeys.banned_users()
        self._set_ban_timestamp(key, user_id, '%s|%s|%s' % (duration, timestamp, username))

    def set_channel_ban_timestamp(self, channel_id: str, user_id: str, duration: str, timestamp: str, username: str) -> None:
        key = RedisKeys.banned_users_channel(channel_id)
        self._set_ban_timestamp(key, user_id, '%s|%s|%s' % (duration, timestamp, username))

    def set_room_ban_timestamp(self, room_id: str, user_id: str, duration: str, timestamp: str, username: str) -> None:
        key = RedisKeys.banned_users(room_id)
        self._set_ban_timestamp(key, user_id, '%s|%s|%s' % (duration, timestamp, username))

    def get_user_roles(self, user_id: str) -> None:
        key = RedisKeys.user_roles()
        cache_key = '%s-%s' % (key, user_id)
        value = self.cache.get(cache_key)
        if value is not None:
            return value

        value = self.redis.hget(key, user_id)
        if value is not None:
            value = json.loads(str(value, 'utf-8'))
            self.cache.set(cache_key, value, ttl=TEN_MINUTES + random.random()*FIVE_MINUTES)
        return value

    def set_user_roles(self, user_id: str, roles: dict) -> None:
        key = RedisKeys.user_roles()
        cache_key = '%s-%s' % (key, user_id)
        self.redis.hset(key, user_id, json.dumps(roles))
        self.cache.set(cache_key, roles, ttl=TEN_MINUTES + random.random()*FIVE_MINUTES)

    def reset_user_roles(self, user_id: str) -> None:
        key = RedisKeys.user_roles()
        cache_key = '%s-%s' % (key, user_id)
        self.redis.hdel(key, user_id)
        self.cache.delete(cache_key)

    def get_admin_room(self) -> Union[str, None]:
        key = RedisKeys.admin_room()
        value = self.cache.get(key)
        if value is not None:
            return value

        room_id = self.redis.get(key)
        if room_id is None or len(str(room_id, 'utf-8').strip()) == 0:
            return None

        room_id = str(room_id, 'utf-8')
        self.cache.set(key, room_id, ttl=EIGHT_HOURS_IN_SECONDS)
        return room_id

    def set_admin_room(self, room_id: str) -> None:
        key = RedisKeys.admin_room()
        self.redis.set(key, room_id)
        self.cache.set(key, room_id, ttl=EIGHT_HOURS_IN_SECONDS)

    def remove_admin_room(self) -> None:
        key = RedisKeys.admin_room()
        self.redis.delete(key)
        self.cache.delete(key)

    def _get_ban_timestamp(self, key: str, user_id: str) -> (str, str, str):
        cache_key = '%s-%s' % (key, user_id)
        value = self.cache.get(cache_key)
        if value is not None:
            return value.split('|', 2)

        ban_info = self.redis.hget(key, user_id)
        if ban_info is None:
            return None, None, None

        ban_info = str(ban_info, 'utf-8')
        return ban_info.split('|', 2)

    def get_global_ban_timestamp(self, user_id: str) -> str:
        key = RedisKeys.banned_users()
        return self._get_ban_timestamp(key, user_id)

    def reset_rooms_for_channel(self, channel_id: str) -> None:
        key_with_info = RedisKeys.rooms_for_channel_with_info(channel_id)
        key_without_info = RedisKeys.rooms_for_channel_without_info(channel_id)

        self.cache.delete(key_with_info)
        self.cache.delete(key_without_info)

        self.redis.delete(key_with_info)
        self.redis.delete(key_without_info)

    def get_rooms_for_channel(self, channel_id: str, with_info: bool = True) -> dict:
        """
        rooms_with_n_users[room_id] = {
            'name': all_rooms[room_id]['name'],
            'sort_order': all_rooms[room_id]['sort_order'],
            'ephemeral': all_rooms[room_id]['ephemeral'],
            'admin': all_rooms[room_id]['admin'],
            'users': len(visible_users)
        }
        """
        if with_info:
            return self._get_rooms_for_channel_with_info(channel_id)
        else:
            return self._get_rooms_for_channel_without_info(channel_id)

    def _get_rooms_for_channel_without_info(self, channel_id: str) -> dict:
        """
        room.uuid: {
            'ephemeral': room.ephemeral,
            'name': room.name
        }
        """
        key = RedisKeys.rooms_for_channel_without_info(channel_id)

        rooms = self.cache.get(key)
        if rooms is not None:
            return rooms

        raw_rooms = self.redis.hgetall(key)
        if raw_rooms is None or len(raw_rooms) == 0:
            return None

        clean_rooms = dict()
        for room_id, room_info in raw_rooms.items():
            room_id = str(room_id, 'utf8')
            room_info = str(room_info, 'utf8')
            room_ephemeral, room_name = room_info.split('|', maxsplit=1)

            if room_ephemeral.lower() in {'', 'true'}:
                room_ephemeral = True
            else:
                room_ephemeral = False

            clean_rooms[room_id] = {
                'name': room_name,
                'ephemeral': room_ephemeral
            }

        return clean_rooms

    def _get_rooms_for_channel_with_info(self, channel_id: str) -> dict:
        """
        rooms_with_n_users[room_id] = {
            'name': all_rooms[room_id]['name'],
            'sort_order': all_rooms[room_id]['sort_order'],
            'ephemeral': all_rooms[room_id]['ephemeral'],
            'admin': all_rooms[room_id]['admin'],
            'users': len(visible_users)
        }
        """
        key = RedisKeys.rooms_for_channel_with_info(channel_id)

        rooms = self.cache.get(key)
        if rooms is not None:
            return rooms

        raw_rooms = self.redis.hgetall(key)
        if raw_rooms is None or len(raw_rooms) == 0:
            return None

        clean_rooms = dict()
        for room_id, room_info in raw_rooms.items():
            room_id = str(room_id, 'utf8')
            room_info = str(room_info, 'utf8')
            room_sort, room_ephemeral, room_admin, room_users, room_name = room_info.split('|', maxsplit=4)

            if room_sort == '':
                room_sort = '999'
            room_sort = int(room_sort)

            if room_admin.lower() in {'', 'false'}:
                room_admin = False
            else:
                room_admin = True

            if room_ephemeral.lower() in {'', 'true'}:
                room_ephemeral = True
            else:
                room_ephemeral = False

            if room_users == '':
                room_users = '0'
            room_users = int(room_users)

            clean_rooms[room_id] = {
                'name': room_name,
                'sort_order': room_sort,
                'ephemeral': room_ephemeral,
                'admin': room_admin,
                'users': room_users
            }

        return clean_rooms

    def set_rooms_for_channel(self, channel_id: str, rooms_infos: dict, with_info: bool = True) -> None:
        if with_info:
            self._set_rooms_for_channel_with_info(channel_id, rooms_infos)
        else:
            self._set_rooms_for_channel_without_info(channel_id, rooms_infos)

    def _set_rooms_for_channel_with_info(self, channel_id: str, rooms_infos: dict) -> None:
        """
        rooms_with_n_users[room_id] = {
            'name': all_rooms[room_id]['name'],
            'sort_order': all_rooms[room_id]['sort_order'],
            'ephemeral': all_rooms[room_id]['ephemeral'],
            'admin': all_rooms[room_id]['admin'],
            'users': len(visible_users)
        }

        room_sort, room_ephemeral, room_admin, room_users, room_name = room_info.split('|', maxsplit=4)
        """
        key = RedisKeys.rooms_for_channel_with_info(channel_id)
        self.cache.set(key, rooms_infos, ttl=TEN_SECONDS)

        redis_rooms = dict()
        for room_id, room_info in rooms_infos.items():
            r_value = '{}|{}|{}|{}|{}'.format(
                str(room_info['sort_order']),
                str(room_info.get('ephemeral', True)).lower(),
                str(room_info.get('admin', False)).lower(),
                str(room_info.get('users', 0)),
                room_info['name']
            )
            redis_rooms[room_id] = r_value

        if len(redis_rooms) > 0:
            self.redis.hmset(key, redis_rooms)
            self.redis.expire(key, ONE_MINUTE)

    def _set_rooms_for_channel_without_info(self, channel_id: str, rooms_infos: dict) -> None:
        """
        room.uuid: {
            'ephemeral': room.ephemeral,
            'name': room.name
        }
        """
        key = RedisKeys.rooms_for_channel_without_info(channel_id)
        self.cache.set(key, rooms_infos, ttl=TEN_SECONDS)

        redis_rooms = dict()
        for room_id, room_info in rooms_infos.items():
            r_value = '{}|{}'.format(
                str(room_info['ephemeral'] or True).lower(),
                room_info['name']
            )
            redis_rooms[room_id] = r_value

        if len(redis_rooms) > 0:
            self.redis.hmset(key, redis_rooms)
            self.redis.expire(key, ONE_MINUTE)

    def get_acls_in_room_for_action(self, room_id: str, action: str) -> dict:
        key = RedisKeys.acls_in_room_for_action(room_id, action)
        return self.cache.get(key)

    def set_acls_in_room_for_action(self, room_id: str, action: str, acls: dict) -> None:
        key = RedisKeys.acls_in_room_for_action(room_id, action)
        self.cache.set(key, acls, ttl=TEN_MINUTES + random.random()*TEN_MINUTES)

    def get_acls_in_channel_for_action(self, channel_id: str, action: str) -> dict:
        key = RedisKeys.acls_in_channel_for_action(channel_id, action)
        return self.cache.get(key)

    def get_users_in_room_for_role(self, room_id: str, role: str) -> dict:
        key = RedisKeys.users_in_room_for_role(room_id, role)
        return self.cache.get(key)

    def set_avatar_for(self, user_id: str, avatar_url: str, app_avatar_url: str, app_avatar_safe_url: str) -> None:
        key = RedisKeys.avatars()
        cache_key = '{}-{}'.format(key, user_id)
        urls = '|'.join([avatar_url, app_avatar_url, app_avatar_safe_url])
        self.cache.set(cache_key, urls, ttl=THIRTY_SECONDS)
        self.redis.hset(key, user_id, urls)

    def get_avatar_for(self, user_id: str) -> Union[Tuple[str, str, str], None]:
        key = RedisKeys.avatars()
        cache_key = '{}-{}'.format(key, user_id)
        value = self.cache.get(cache_key)
        if value is not None:
            return value.split('|', maxsplit=2)

        value = self.redis.hget(key, user_id)
        if value is None:
            return None

        value = str(value, 'utf-8')
        avatar_url, app_avatar_url, app_avatar_safe_url = value.split('|', maxsplit=2)

        self.cache.set(cache_key, value, ttl=THIRTY_SECONDS)
        return avatar_url, app_avatar_url, app_avatar_safe_url

    def reset_sids_for_user(self, user_id: str) -> None:
        key = RedisKeys.sid_for_user_id()
        self.redis.hdel(key, user_id)

    def remove_sid_for_user(self, user_id: str, sid: str) -> None:
        def _try_to_remove_sid(sid_to_remove):
            sid_key = RedisKeys.user_id_for_sid()
            self.redis.hdel(sid_key, sid_to_remove)

            if user_id is None:
                return

            all_sids = self.get_sids_for_user(user_id)
            if all_sids is None:
                all_sids = set()

            if sid_to_remove not in all_sids:
                return

            all_sids.remove(sid_to_remove)
            all_sids = ','.join(list(set(all_sids)))

            key = RedisKeys.sid_for_user_id()
            self.redis.hset(key, user_id, all_sids)

        try:
            _try_to_remove_sid(sid)
        except RuntimeError:
            try:
                _try_to_remove_sid(sid)
            except RuntimeError as e:
                logger.error('could not remove sid {} for user {}, tried 2 times: {}'.format(sid, user_id, str(e)))
                logger.exception(traceback.format_exc())

    def set_sids_for_user(self, user_id: str, all_sids: list) -> None:
        key = RedisKeys.sid_for_user_id()
        all_sids = set(all_sids.copy())

        sid_key = RedisKeys.user_id_for_sid()
        for sid in all_sids:
            self.redis.hset(sid_key, sid, user_id)

        all_sids = ','.join(list(set(all_sids)))
        self.redis.hset(key, user_id, all_sids)

    def add_sid_for_user(self, user_id: str, sid: str) -> None:
        all_sids = self.get_sids_for_user(user_id)
        if all_sids is None:
            all_sids = set()
        else:
            all_sids = set(all_sids)

        all_sids.add(sid)

        key = RedisKeys.sid_for_user_id()
        sid_key = RedisKeys.user_id_for_sid()
        for sid in all_sids:
            self.redis.hset(sid_key, sid, user_id)

        all_sids = ','.join(list(set(all_sids)))
        self.redis.hset(key, user_id, all_sids)

    def get_user_for_sid(self, sid: str):
        sid_key = RedisKeys.user_id_for_sid()
        user_id = self.redis.hget(sid_key, sid)
        if user_id is not None:
            user_id = str(user_id, 'utf-8')
        return user_id

    def get_sids_for_user(self, user_id: str) -> Union[None, list]:
        key = RedisKeys.sid_for_user_id()
        all_sids = self.redis.hget(key, user_id)
        if all_sids is None:
            return None

        all_sids = list(set(str(all_sids, 'utf-8').split(',')))
        return all_sids.copy()

    def get_users_in_room(self, room_id: str, is_super_user: bool) -> dict:
        if is_super_user:
            key = RedisKeys.users_in_room_incl_invisible(room_id)
        else:
            key = RedisKeys.users_in_room_only_visible(room_id)
        return self.cache.get(key)

    def set_users_in_room(self, room_id: str, users: dict, is_super_user: bool) -> None:
        if is_super_user:
            key = RedisKeys.users_in_room_incl_invisible(room_id)
        else:
            key = RedisKeys.users_in_room_only_visible(room_id)
        self.cache.set(key, users, ttl=TEN_SECONDS + random.random()*TEN_SECONDS)

    def set_users_in_room_for_role(self, room_id: str, role: str, users: dict) -> None:
        key = RedisKeys.users_in_room_for_role(room_id, role)
        self.cache.set(key, users, ttl=TEN_MINUTES + random.random()*TEN_MINUTES)

    def reset_users_in_room_for_role(self, room_id: str, role: str) -> None:
        key = RedisKeys.users_in_room_for_role(room_id, role)
        self.cache.delete(key)

    def get_users_in_channel_for_role(self, channel_id: str, role: str) -> dict:
        key = RedisKeys.users_in_channel_for_role(channel_id, role)
        return self.cache.get(key)

    def set_users_in_channel_for_role(self, channel_id: str, role: str, users: dict) -> None:
        key = RedisKeys.users_in_channel_for_role(channel_id, role)
        self.cache.set(key, users, ttl=TEN_MINUTES + random.random()*TEN_MINUTES)

    def reset_users_in_channel_for_role(self, channel_id: str, role: str) -> None:
        key = RedisKeys.users_in_channel_for_role(channel_id, role)
        self.cache.delete(key)

    def set_acls_in_channel_for_action(self, channel_id: str, action: str, acls: dict) -> None:
        key = RedisKeys.acls_in_channel_for_action(channel_id, action)
        self.cache.set(key, acls, ttl=FIVE_MINUTES)

    def reset_acls_in_channel_for_action(self, channel_id: str, action: str) -> None:
        key = RedisKeys.acls_in_channel_for_action(channel_id, action)
        self.cache.delete(key)

    def reset_acls_in_room_for_action(self, room_id: str, action: str) -> None:
        key = RedisKeys.acls_in_room_for_action(room_id, action)
        self.cache.delete(key)

    def reset_acls_in_channel(self, channel_id: str) -> None:
        key = RedisKeys.acls_in_channel(channel_id)
        self.cache.delete(key)

    def reset_acls_in_room(self, room_id: str) -> None:
        key = RedisKeys.acls_in_room(room_id)
        self.cache.delete(key)

    def set_all_acls_for_channel(self, channel_id: str, acls: dict) -> None:
        key = RedisKeys.acls_in_channel(channel_id)
        self.cache.set(key, acls, ttl=FIVE_MINUTES + random.random()*FIVE_MINUTES)

    def set_all_acls_for_room(self, room_id: str, acls: dict) -> None:
        key = RedisKeys.acls_in_room(room_id)
        self.cache.set(key, acls, ttl=FIVE_MINUTES + random.random()*FIVE_MINUTES)

    def get_all_acls_for_channel(self, channel_id: str) -> dict:
        key = RedisKeys.acls_in_channel(channel_id)
        return self.cache.get(key)

    def get_all_acls_for_room(self, room_id: str) -> dict:
        key = RedisKeys.acls_in_room(room_id)
        return self.cache.get(key)

    def reset_channels_with_sort(self):
        key = RedisKeys.channels_with_sort()
        self.cache.delete(key)
        self.redis.delete(key)

    def set_all_rooms(self, all_rooms):
        key = RedisKeys.all_rooms()
        self.cache.delete(key)
        self.cache.set(key, all_rooms, ttl=ONE_MINUTE)

    def get_all_rooms(self) -> Union[List, None]:
        key = RedisKeys.all_rooms()
        return self.cache.get(key)

    def get_can_whisper_to_user(self, sender_id: str, target_user_name: str) -> Union[None, bool]:
        key = RedisKeys.can_whisper_to(sender_id)
        cache_key = '%s-%s' % (key, target_user_name)

        can_whisper = self.cache.get(cache_key)
        if can_whisper is not None:
            return can_whisper

        can_whisper = self.redis.hget(key, target_user_name)
        can_whisper = str(can_whisper, 'utf-8')

        return can_whisper == '1'

    def set_can_whisper_to_user(self, sender_id: str, target_user_name: str, allowed: bool) -> None:
        # if not allowed, we need to check remote system, maybe they will soon be allowed
        if not allowed:
            return

        key = RedisKeys.can_whisper_to(sender_id)
        cache_key = '%s-%s' % (key, target_user_name)

        self.cache.set(cache_key, allowed, ttl=ONE_HOUR)
        self.redis.hset(key, target_user_name, '1' if allowed else '0')
        self.redis.expire(key, EIGHT_HOURS_IN_SECONDS)

    def get_channels_with_sort(self):
        key = RedisKeys.channels_with_sort()
        channels = self.cache.get(key)
        if channels is not None:
            return channels

        raw_channels = self.redis.hgetall(key)
        clean_channels = dict()

        if raw_channels is None or len(raw_channels) == 0:
            return None

        for channel_id, channel_sort_channel_name in raw_channels.items():
            try:
                channel_sort_channel_name = str(channel_sort_channel_name, 'utf8')
                channel_sort, channel_tags, channel_name = channel_sort_channel_name.split('|', maxsplit=2)
                channel_sort = int(channel_sort)
                channel_id = str(channel_id, 'utf8')

                if channel_tags == 'None':
                    channel_tags = ''

                clean_channels[channel_id] = (channel_name, channel_sort, channel_tags)
            except Exception as e:
                logger.error('invalid channel name in redis with key {}, value was "{}": {}'.format(
                    key, channel_sort_channel_name, str(e)))

        self.cache.set(key, clean_channels, ttl=ONE_MINUTE)
        return clean_channels

    def set_channels_with_sort(self, channels):
        if len(channels) == 0:
            return

        key = RedisKeys.channels_with_sort()
        self.cache.set(key, channels, ttl=ONE_MINUTE)

        redis_channels = dict()
        for channel_id, (channel_name, channel_sort, tags) in channels.items():
            redis_channels[channel_id] = '{}|{}|{}'.format(str(channel_sort), tags, channel_name)

        self.redis.hmset(key, redis_channels)
        self.redis.expire(key, ONE_MINUTE)

    def get_channel_ban_timestamp(self, channel_id: str, user_id: str) -> str:
        key = RedisKeys.banned_users_channel(channel_id)
        return self._get_ban_timestamp(key, user_id)

    def get_room_ban_timestamp(self, room_id: str, user_id: str) -> str:
        key = RedisKeys.banned_users(room_id)
        return self._get_ban_timestamp(key, user_id)

    def remove_room_id_for_name(self, channel_id: str, room_name: str) -> None:
        key = RedisKeys.room_id_for_name(channel_id)
        cache_key = '%s-%s' % (key, room_name)
        self.cache.delete(cache_key)
        self.redis.hdel(key, room_name)

    def get_room_id_for_name(self, channel_id: str, room_name: str) -> str:
        key = RedisKeys.room_id_for_name(channel_id)
        cache_key = '%s-%s' % (key, room_name)
        value = self.cache.get(cache_key)
        if value is not None:
            return value

        value = self.redis.hget(key, room_name)
        if value is None:
            return None

        value = str(value, 'utf-8')
        self.cache.set(cache_key, value)
        return value

    def set_room_id_for_name(self, channel_id, room_name, room_id):
        key = RedisKeys.room_id_for_name(channel_id)
        cache_key = '%s-%s' % (key, room_name)
        self.cache.set(cache_key, room_id)
        self.redis.hset(key, room_name, room_id)

    def get_user_name(self, user_id: str) -> str:
        key = RedisKeys.user_names()
        cache_key = '%s-%s' % (key, user_id)
        value = self.cache.get(cache_key)
        if value is not None:
            return value

        user_name = self.redis.hget(key, user_id)
        if user_name is not None:
            user_name = str(user_name, 'utf-8')
            self.cache.set(cache_key, user_name)
            return user_name
        return user_name

    def set_user_name(self, user_id: str, user_name: str):
        key = RedisKeys.user_names()
        cache_key = '%s-%s' % (key, user_id)
        self.redis.hset(key, user_id, user_name)
        self.cache.set(cache_key, user_name)

    def get_room_exists(self, channel_id, room_id):
        key = RedisKeys.rooms(channel_id)
        cache_key = '%s-%s' % (key, room_id)
        value = self.cache.get(cache_key)
        if value is not None:
            return True

        exists = self.redis.hexists(key, room_id)
        if exists == 1:
            self.cache.set(cache_key, True)
            return True
        return None

    def remove_channel_exists(self, channel_id: str) -> None:
        key = RedisKeys.channel_exists()
        cache_key = '%s-%s' % (key, channel_id)
        self.redis.hdel(key, channel_id)
        self.cache.delete(cache_key)

        key = RedisKeys.channels()
        cache_key = '%s-name-%s' % (key, channel_id)
        self.cache.delete(cache_key)
        self.redis.hdel(key, channel_id)

    def remove_room_exists(self, channel_id, room_id):
        key = RedisKeys.rooms(channel_id)
        cache_key = '%s-%s' % (key, room_id)
        self.cache.set(cache_key, None)
        self.redis.hdel(key, room_id)

        key = RedisKeys.channel_for_rooms()
        cache_key = '%s-%s' % (key, room_id)
        self.cache.delete(cache_key)
        self.redis.hdel(key, room_id)

        key = RedisKeys.room_roles(room_id)
        self.redis.delete(key)

        key = RedisKeys.room_name_for_id()
        cache_key = '%s-%s-name' % (key, room_id)

        room_name = self.redis.hget(key, room_id)
        if room_name is not None:
            try:
                room_name = str(room_name, 'utf-8')
            except Exception:
                pass

        self.cache.delete(cache_key)
        self.redis.hdel(key, room_id)

        key = RedisKeys.room_id_for_name(channel_id)
        self.redis.hdel(key, room_id)

        if room_name is not None:
            cache_key = '%s-%s' % (key, room_name)
            self.cache.delete(cache_key)

        for role in RoleKeys.all_roles:
            key = RedisKeys.users_in_room_for_role(room_id, role)
            self.redis.delete(key)

    def set_room_exists(self, channel_id, room_id, room_name):
        key = RedisKeys.rooms(channel_id)
        cache_key = '%s-%s' % (key, room_id)
        self.cache.set(cache_key, room_name)
        self.redis.hset(key, room_id, room_name)
        self.redis.expire(key, ONE_MINUTE)

    def set_channel_exists(self, channel_id: str) -> None:
        key = RedisKeys.channel_exists()
        cache_key = '%s-%s' % (key, channel_id)
        self.redis.hset(key, channel_id, True)
        self.redis.expire(key, ONE_MINUTE)
        self.cache.set(cache_key, True)

    def set_channel_for_room(self, channel_id: str, room_id: str) -> None:
        key = RedisKeys.channel_for_rooms()
        cache_key = '%s-%s' % (key, room_id)
        self.redis.hset(key, room_id, channel_id)
        self.redis.expire(key, ONE_HOUR)
        self.cache.set(cache_key, channel_id, ttl=ONE_HOUR)

    def get_channel_exists(self, channel_id):
        key = RedisKeys.channel_exists()
        cache_key = '%s-%s' % (key, channel_id)
        value = self.cache.get(cache_key)
        if value is not None:
            return True

        value = self.redis.hget(key, channel_id)
        if value is None:
            return None

        self.cache.set(cache_key, True)
        return True

    def set_channel_name(self, channel_id: str, channel_name: str) -> None:
        key = RedisKeys.channels()
        cache_key = '%s-name-%s' % (key, channel_id)
        self.cache.set(cache_key, channel_name)
        self.redis.hset(key, channel_id, channel_name)
        self.redis.expire(key, TEN_MINUTES)

    def get_channel_name(self, channel_id: str) -> str:
        key = RedisKeys.channels()
        cache_key = '%s-name-%s' % (key, channel_id)
        value = self.cache.get(cache_key)
        if value is not None:
            return value

        value = self.redis.hget(key, channel_id)
        if value is None:
            return None

        value = str(value, 'utf-8')
        self.cache.set(cache_key, value)
        return value

    def get_room_name(self, room_id: str) -> str:
        key = RedisKeys.room_name_for_id()
        cache_key = '%s-%s-name' % (key, room_id)
        value = self.cache.get(cache_key)
        if value is not None:
            return value

        value = self.redis.hget(key, room_id)
        if value is None:
            return None

        value = str(value, 'utf-8')
        self.cache.set(cache_key, value)
        return value

    def set_room_name(self, room_id: str, room_name: str) -> None:
        key = RedisKeys.room_name_for_id()
        cache_key = '%s-%s-name' % (key, room_id)
        self.cache.set(cache_key, room_name, ttl=TEN_MINUTES + random.random()*FIVE_MINUTES)
        self.redis.hset(key, room_id, room_name)
        self.redis.expire(key, TEN_MINUTES)

    def get_channel_for_room(self, room_id):
        key = RedisKeys.channel_for_rooms()
        cache_key = '%s-%s' % (key, room_id)
        value = self.cache.get(cache_key)
        if value is not None:
            return value

        channel_id = self.redis.hget(key, room_id)
        if channel_id is None:
            return None

        channel_id = str(channel_id, 'utf-8')
        self.cache.set(cache_key, channel_id)
        return channel_id

    def get_user_status(self, user_id: str):
        key = RedisKeys.user_status(user_id)
        status = self.redis.get(key)
        if status is None or status == '':
            return None

        return str(status, 'utf-8')

    def set_user_status(self, user_id: str, status: str) -> None:
        key = RedisKeys.user_status(user_id)
        self.redis.set(key, status)

    def get_user_info(self, user_id: str) -> dict:
        key = RedisKeys.auth_key(user_id)
        return self.cache.get(key)

    def set_user_info(self, user_id: str, info: dict) -> None:
        key = RedisKeys.auth_key(user_id)
        self.cache.set(key, info, ttl=ONE_HOUR)

    def reset_user_info(self, user_id: str) -> None:
        key = RedisKeys.auth_key(user_id)
        self.cache.delete(key)

    def user_check_status(self, user_id, other_status):
        return self.get_user_status(user_id) == other_status

    def user_is_offline(self, user_id):
        return self.user_check_status(user_id, UserKeys.STATUS_UNAVAILABLE)

    def user_is_online(self, user_id):
        return self.user_check_status(user_id, UserKeys.STATUS_AVAILABLE)

    def user_is_invisible(self, user_id):
        return self.user_check_status(user_id, UserKeys.STATUS_INVISIBLE)

    def user_is_in_multicast(self, user_id):
        return self.redis.sismember(RedisKeys.users_multi_cast(), str(user_id))

    def remove_from_multicast_on_disconnect(self, user_id: str) -> None:
        try:
            user_id_str = str(user_id).strip()
            self.redis.srem(RedisKeys.users_multi_cast(), user_id_str)
        except Exception as e:
            logger.error('could remove user form multicast: %s' % str(e))
            logger.exception(traceback.format_exc())
            raise e  # force catch from caller

    def set_user_offline(self, user_id: str) -> None:
        try:
            user_id_str = str(user_id).strip()
            user_id_int = int(float(user_id))
            self.cache.set(RedisKeys.user_status(user_id_str), UserKeys.STATUS_UNAVAILABLE)
            self.redis.setbit(RedisKeys.online_bitmap(), user_id_int, 0)
            self.redis.srem(RedisKeys.online_set(), user_id_str)
            self.redis.srem(RedisKeys.users_multi_cast(), user_id_str)
            self.redis.set(RedisKeys.user_status(user_id_str), UserKeys.STATUS_UNAVAILABLE)
        except Exception as e:
            logger.error('could not set_user_offline(): %s' % str(e))
            logger.exception(traceback.format_exc())
            raise e  # force catch from caller

    def set_user_online(self, user_id: str) -> None:
        try:
            user_id_str = str(user_id).strip()
            user_id_int = int(float(user_id))
            self.cache.set(RedisKeys.user_status(user_id_str), UserKeys.STATUS_AVAILABLE)
            self.redis.setbit(RedisKeys.online_bitmap(), user_id_int, 1)
            self.redis.sadd(RedisKeys.online_set(), user_id_str)
            self.redis.sadd(RedisKeys.users_multi_cast(), user_id_str)
            self.redis.set(RedisKeys.user_status(user_id_str), UserKeys.STATUS_AVAILABLE)
        except Exception as e:
            logger.error('could not set_user_online(): %s' % str(e))
            logger.exception(traceback.format_exc())

    def set_user_status_invisible(self, user_id: str) -> None:
        try:
            user_id_str = str(user_id).strip()
            self.cache.set(RedisKeys.user_status(user_id_str), UserKeys.STATUS_INVISIBLE)
            self.redis.set(RedisKeys.user_status(user_id_str), UserKeys.STATUS_INVISIBLE)
        except Exception as e:
            logger.error('could not set_user_status_invisible(): %s' % str(e))
            logger.exception(traceback.format_exc())

    def set_user_invisible(self, user_id: str) -> None:
        try:
            user_id_str = str(user_id).strip()
            user_id_int = int(float(user_id))
            self.cache.set(RedisKeys.user_status(user_id_str), UserKeys.STATUS_INVISIBLE)
            self.redis.setbit(RedisKeys.online_bitmap(), user_id_int, 0)
            self.redis.srem(RedisKeys.online_set(), user_id_str)
            self.redis.sadd(RedisKeys.users_multi_cast(), user_id_str)
            self.redis.set(RedisKeys.user_status(user_id_str), UserKeys.STATUS_INVISIBLE)
        except Exception as e:
            logger.error('could not set_user_invisible(): %s' % str(e))
            logger.exception(traceback.format_exc())

    def set_session_count(self, session_count: int) -> None:
        node_key = '{}-{}'.format(self.listen_host, self.listen_port)
        self.redis.hset(RedisKeys.session_count(), node_key, session_count)
