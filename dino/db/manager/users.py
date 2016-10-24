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
