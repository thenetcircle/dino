import logging
import traceback
from datetime import datetime
from typing import Optional
from uuid import uuid4 as uuid

from dino import utils
from dino.config import ConfigKeys
from dino.db.manager.base import BaseManager
from dino.environ import GNEnvironment
from dino.exceptions import NoSuchUserException
from dino.exceptions import UnknownBanTypeException
from dino.utils import ActivityBuilder

logger = logging.getLogger(__name__)


def created_activity(user_id: str, user_name: str, target_id: str, target_name: str, session_ids: list, namespace: str) -> dict:
    user_name = utils.b64e(user_name)
    target_name = utils.b64e(target_name)

    return ActivityBuilder.enrich({
        "actor": {
            "id": user_id,
            "content": ",".join(session_ids),
            "displayName": user_name,
            "objectType": "user",
            "url": namespace
        },
        "object": {
            "id": user_id,
            "displayName": user_name,
            "url": namespace
        },
        "verb": "created",
        "target": {
            "id": target_id,
            "displayName": target_name,
            "content": "out_of_scope",
            "objectType": "room"
        }
    })


def join_activity(user_id: str, user_name: str, target_id: str, session_ids: list, namespace: str) -> dict:
    user_name = utils.b64e(user_name)

    return ActivityBuilder.enrich({
        "actor": {
            "id": user_id,
            "content": ",".join(session_ids),
            "displayName": user_name,
            "url": namespace
        },
        "object": {
            "id": user_id,
            "displayName": user_name,
            "objectType": "user",
            "url": namespace
        },
        "verb": "join",
        "target": {
            "id": target_id,
            "content": "out_of_scope",
            "objectTYpe": "room"
        }
    })


def leave_activity(user_id: str, user_name: str, target_id: str, session_ids: list, namespace: str) -> dict:
    user_name = utils.b64e(user_name)

    return ActivityBuilder.enrich({
        "actor": {
            "id": user_id,
            "content": ",".join(session_ids),
            "displayName": user_name,
            "url": namespace
        },
        "object": {
            "id": user_id,
            "displayName": user_name,
            "objectType": "user",
            "url": namespace
        },
        "verb": "leave",
        "target": {
            "id": target_id,
            "content": "out_of_scope",
            "objectTYpe": "room"
        }
    })


class UserManager(BaseManager):
    def __init__(self, env: GNEnvironment):
        self.env = env

    def auth_user(self, user_id, _):
        self.env.cache.add_heartbeat(user_id)

    def get_users_for_room(self, room_id: str) -> list:
        users = self.env.db.users_in_room(room_id, skip_cache=True)
        output = list()

        for user_id, user_name in users.items():
            output.append({
                'uuid': user_id,
                'name': user_name
            })
        return output

    def del_super_user(self, user_uuid: str) -> None:
        self.env.db.remove_super_user(user_uuid)

    def set_super_user(self, user_uuid: str) -> None:
        self.env.db.set_super_user(user_uuid)

    def search_for(self, query: str) -> list:
        users = self.env.db.search_for_users(query)
        output = list()
        for user in users:
            output.append({
                'uuid': user['uuid'],
                'name': user['name']
            })
        return output

    def join_room(self, user_id, user_name, room_id, session_ids, namespace) -> None:
        data = join_activity(user_id, user_name, room_id, session_ids, namespace)
        self.env.publish(data)

    def room_created(self, user_id, user_name, room_id, room_name, session_ids, namespace) -> None:
        data = created_activity(user_id, user_name, room_id, room_name, session_ids, namespace)
        self.env.publish(data)

    def leave_room(self, user_id, user_name, room_id, session_ids, namespace) -> None:
        data = leave_activity(user_id, user_name, room_id, session_ids, namespace)
        self.env.publish(data)

    def kick_user(
            self, room_id: Optional[str], user_id: str, reason: str = None, admin_id: str = None, room_name: str = None
    ) -> None:
        # TODO: support get room_id from room name

        if room_name is None:
            try:
                room_name = self.env.db.get_room_name(room_id)
            except Exception as e:
                logger.error('could not get room name for room uuid %s: %s' % (room_id, str(e)))
                raise e

        elif room_id is None:
            room_id = utils.get_room_id(room_name, use_default_channel=True)

        try:
            user_name = self.env.db.get_user_name(user_id)
        except Exception as e:
            logger.error('could not get user name for user id %s: %s' % (user_id, str(e)))
            raise e

        kick_activity = {
            'actor': {
                'id': '0',
                'displayName': utils.b64e('admin')
            },
            'verb': 'kick',
            'object': {
                'id': user_id,
                'displayName': utils.b64e(user_name)
            },
            'target': {
                'id': room_id,
                'displayName': utils.b64e(room_name),
                'objectType': 'room',
                'url': '/ws'
            },
            'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
            'id': str(uuid())
        }

        if admin_id is not None:
            kick_activity['actor']['id'] = admin_id

        if reason is not None:
            if utils.is_base64(reason):
                kick_activity['object']['content'] = reason
            else:
                logger.warning('reason is not base64, ignoring')

        self.env.publish(kick_activity)

    def ban_user(
            self, user_id: str, target_id: str, duration: str, target_type: str,
            reason: str = None, banner_id: str = None, user_name: str = None, target_name: str = None
    ) -> None:
        if target_type not in {'global', 'channel', 'room'}:
            raise UnknownBanTypeException(target_type)

        if target_name is None:
            if target_type == 'channel':
                target_name = self.env.db.get_channel_name(target_id)

            elif target_type == 'room':
                target_name = self.env.db.get_room_name(target_id)

        try:
            user_name = utils.b64e(self.env.db.get_user_name(user_id))
        except NoSuchUserException:
            logger.info('when processing ban request: user %s does not exist, will create' % user_id)
            user_name = user_name or user_id
            self.env.db.create_user(user_id, user_name)

        ban_activity = {
            'actor': {
                'id': '0',
                'displayName': utils.b64e('admin')
            },
            'verb': 'ban',
            'object': {
                'id': user_id,
                'displayName': user_name,
                'summary': duration,
                'updated': utils.ban_duration_to_datetime(duration).strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
            },
            'target': {
                'url': '/ws',
                'objectType': target_type
            },
            'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
            'id': str(uuid())
        }

        if reason is not None:
            ban_activity['object']['content'] = reason

        if banner_id is not None:
            ban_activity['actor']['id'] = banner_id

        if target_name is not None:
            ban_activity['target']['id'] = target_id
            ban_activity['target']['displayName'] = utils.b64e(target_name)

        self.env.publish(ban_activity)

    def remove_ban(self, user_id: str, target_id: str, target_type: str) -> None:
        ban_activity = {
            'actor': {
                'id': '0',
                'displayName': utils.b64e('admin')
            },
            'verb': 'unban',
            'object': {
                'id': user_id,
                'displayName': utils.b64e(utils.get_user_name_for(user_id))
            },
            'target': {
                'objectType': target_type
            },
            'id': str(uuid()),
            'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
        }

        if target_type == 'global':
            self.env.db.remove_global_ban(user_id)

        elif target_type == 'channel':
            self.env.db.remove_channel_ban(target_id, user_id)
            ban_activity['target']['id'] = target_id
            ban_activity['target']['displayName'] = utils.b64e(utils.get_channel_name(target_id))

        elif target_type == 'room':
            self.env.db.remove_room_ban(target_id, user_id)
            ban_activity['target']['id'] = target_id
            ban_activity['target']['displayName'] = utils.b64e(utils.get_room_name(target_id))

        else:
            raise UnknownBanTypeException(target_type)

        self.env.publish(ban_activity)

    def get_banned_users(self) -> dict:
        return self.env.db.get_banned_users()

    def add_channel_admin(self, channel_id: str, user_id: str) -> None:
        self.env.db.set_admin(channel_id, user_id)

    def add_channel_owner(self, channel_id: str, user_id: str) -> None:
        self.env.db.set_owner_channel(channel_id, user_id)

    def add_room_moderator(self, room_id: str, user_id: str) -> None:
        self.env.db.set_moderator(room_id, user_id)

    def add_room_owner(self, room_id: str, user_id: str) -> None:
        self.env.db.set_owner(room_id, user_id)

    def remove_channel_admin(self, channel_id: str, user_id: str) -> None:
        self.env.db.remove_admin(channel_id, user_id)

    def remove_channel_owner(self, channel_id: str, user_id: str) -> None:
        self.env.db.remove_owner_channel(channel_id, user_id)

    def remove_room_moderator(self, room_id: str, user_id: str) -> None:
        self.env.db.remove_moderator(room_id, user_id)

    def remove_room_owner(self, room_id: str, user_id: str) -> None:
        self.env.db.remove_owner(room_id, user_id)

    def create_super_user(self, user_name: str, user_id: str) -> None:
        try:
            self.env.db.create_user(user_id, user_name)
            self.env.db.set_super_user(user_id)
        except Exception as e:
            logger.exception(traceback.format_exc())
            logger.error('could not create super user: %s' % str(e))

    def get_user(self, user_id: str) -> dict:
        user_name = self.env.db.get_user_name(user_id)
        return {
            'uuid': user_id,
            'name': utils.b64e(user_name)
        }

    def _get_user(self, user_id: str, user_name: str) -> dict:
        return {
            'uuid': user_id,
            'name': user_name
        }

    def get_super_users(self) -> list:
        users = self.env.db.get_super_users()
        output = list()
        for user_id, user_name in users.items():
            output.append(self._get_user(user_id, user_name))
        return output
