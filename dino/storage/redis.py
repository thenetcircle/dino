from zope.interface import implementer
from activitystreams.models.activity import Activity

from dino.storage import IStorage
from dino.config import ConfigKeys
from dino.config import SessionKeys
from dino.config import AckStatus
from dino.config import RedisKeys
from dino.utils import is_base64
from dino.utils import b64d
from dino.utils import b64e

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


@implementer(IStorage)
class StorageRedis(object):
    redis = None

    def __init__(self, host: str, port: int = 6379, db: int = 0, env=None):
        if env is None:
            from dino import environ
            env = environ.env

        self.env = env

        if self.env.config.get(ConfigKeys.TESTING, False) or host == 'mock':
            from fakeredis import FakeRedis as Redis
        else:
            from redis import Redis

        self.redis = Redis(host=host, port=port, db=db)

    def store_message(self, activity: Activity, deleted=False) -> None:
        target_id = activity.target.id
        target_name = b64e(activity.target.display_name)
        user_id = self.env.session.get(SessionKeys.user_id.value)
        user_name = b64e(self.env.session.get(SessionKeys.user_name.value))
        channel_id = activity.object.url
        channel_name = b64e(activity.object.summary)
        msg = activity.object.content

        if not is_base64(msg):
            raise RuntimeError('message is not base64')

        self.redis.lpush(
                RedisKeys.room_history(target_id),
                '%s,%s,%s,%s,%s,%s,%s,%s' % (
                    activity.id, activity.published, user_id, user_name, target_name, channel_id, channel_name, msg))

        max_history = self.env.config.get(ConfigKeys.LIMIT, domain=ConfigKeys.HISTORY, default=-1)
        if max_history > 0:
            self.redis.ltrim(RedisKeys.room_history(target_id), 0, max_history)

    def get_undeleted_message_ids_for_user(self, user_id: str):
        raise NotImplementedError('inefficient query for redis storage, not implemented')

    def delete_message(self, message_id: str, room_id: str=None):
        if room_id is None:
            raise RuntimeError('redis storage needs room_id parameter to delete message')

        if message_id is None or message_id == '':
            return

        all_history = self.redis.lrange(RedisKeys.room_history(room_id), 0, -1)
        found_msg = None
        for history in all_history:
            history = str(history, 'utf-8')
            if history.startswith(message_id + ','):
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
            msg_id, published, user_id, user_name, target_name, channel_id, channel_name, msg = \
                message_entry.split(',', 7)

            cleaned_messages.append({
                'message_id': msg_id,
                'from_user_id': user_id,
                'from_user_name': b64d(user_name),
                'target_id': room_id,
                'target_name': b64d(target_name),
                'body': b64d(msg),
                'domain': 'room',
                'channel_id': channel_id,
                'channel_name': b64d(channel_name),
                'timestamp': published,
                'deleted': False
            })

        return cleaned_messages

    def _get_acks_for(self, message_ids: set, receiver_id: str) -> dict:
        redis_key = RedisKeys.ack_for_user(receiver_id)
        acks = dict()
        for message_id in message_ids:
            ack = self.redis.hget(redis_key, message_id)
            if ack is None:
                continue
            acks[message_ids] = int(float(str(ack, 'utf-8')))
        return acks

    def _update_acks_with_status(self, message_ids: set, receiver_id: str, target_id: str, status: int):
        redis_key_user = RedisKeys.ack_for_user(receiver_id)
        redis_key_room = RedisKeys.ack_for_room(target_id)

        for message_id in message_ids:
            self.redis.hset(redis_key_user, message_id, str(status))
            self.redis.sadd(redis_key_room, message_id)

    def _mark_as_status(self, message_ids: set, receiver_id: str, target_id: str, status: int):
        current_acks = self._get_acks_for(message_ids, receiver_id)
        to_update = list()
        to_add = list()

        for message_id in message_ids:
            if message_id not in current_acks:
                to_add.append(message_id)
                continue
                # don't downgrade status
            if current_acks.get(message_id) >= status:
                continue
            to_update.append(message_id)

        if len(to_update) > 0:
            self._update_acks_with_status(message_ids, receiver_id, target_id, status)
        if len(to_add) > 0:
            self._update_acks_with_status(message_ids, receiver_id, target_id, status)

    def get_unacked_history(self, user_id: str) -> list:
        """
        redis_key_user = RedisKeys.ack_for_user(user_id)
        redis_key_room = RedisKeys.ack_for_room(target_id)
        acks = self.redis.hgetall(redis_key_user)
        msg_ids = {str(msg_id, 'utf-8') for msg_id, ack in acks if int(float(str(ack, 'utf-8'))) == AckStatus.NOT_ACKED}
        """
        return list()

    def mark_as_received(self, message_ids: set, receiver_id: str, target_id: str) -> None:
        self._mark_as_status(message_ids, receiver_id, target_id, AckStatus.RECEIVED)

    def mark_as_read(self, message_ids: set, receiver_id: str, target_id: str) -> None:
        self._mark_as_status(message_ids, receiver_id, target_id, AckStatus.READ)

    def mark_as_unacked(self, message_id: str, receiver_id: str, target_id: str) -> None:
        self._mark_as_status({message_id}, receiver_id, target_id, AckStatus.NOT_ACKED)

    def get_history_for_time_slice(self, room_id: str, from_time: int, to_time: int) -> list:
        raise NotImplementedError()

    def get_unread_history(self, room_id: str, time_stamp: int, limit: int = 100) -> list:
        raise NotImplementedError()
