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

from dino.db.manager.base import BaseManager
from dino.environ import GNEnvironment
from dino.utils import ban_duration_to_timestamp
from dino.exceptions import UnknownBanType

import traceback
import logging

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


class UserManager(BaseManager):
    def __init__(self, env: GNEnvironment):
        self.env = env

    def get_users_for_room(self, room_id: str) -> list:
        users = self.env.db.users_in_room(room_id)
        output = list()

        for user_id, user_name in users.items():
            output.append({
                'uuid': user_id,
                'name': user_name
            })
        return output

    def ban_user(self, user_id: str, target_id: str, duration: str, target_type: str):
        timestamp = ban_duration_to_timestamp(duration)
        if target_type == 'global':
            self.env.db.ban_user_global(user_id, timestamp, duration)
        elif target_type == 'channel':
            self.env.db.ban_user_channel(user_id, timestamp, duration, target_id)
        elif target_type == 'room':
            self.env.db.ban_user_room(user_id, timestamp, duration, target_id)
        else:
            raise UnknownBanType(target_type)

    def get_banned_users(self) -> dict:
        try:
            return self.env.db.get_banned_users()
        except Exception as e:
            logger.error('could not get banned users: %s' % str(e))
            return {
                'global': dict(),
                'channels': dict(),
                'rooms': dict()
            }

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

    def create_admin_user(self, user_name: str, user_id: str) -> None:
        try:
            self.env.db.create_user(user_id, user_name)
            self.env.db.set_super_user(user_id)
        except Exception as e:
            logger.error('could not create user: %s' % str(e))
            print(traceback.format_exc())

    def get_user(self, user_uuid: str) -> dict:
        return {
            'uuid': 'todo',
            'name': 'todo'
        }

    def get_super_users(self) -> dict:
        try:
            users = self.env.db.get_super_users()
        except Exception as e:
            logger.error('could not get super users: %s' % str(e))
            print(traceback.format_exc())
            return dict()

        output = list()
        for user_id, user_name in users.items():
            output.append({
                'uuid': user_id,
                'name': user_name
            })
        return output
