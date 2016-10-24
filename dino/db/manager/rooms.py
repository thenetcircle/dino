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

import logging
import traceback

from dino.db.manager.base import BaseManager
from dino.environ import GNEnvironment

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


class RoomManager(BaseManager):
    def __init__(self, env: GNEnvironment):
        self.env = env

    def get_rooms(self, channel_id: str) -> list:
        try:
            rooms = self.env.db.rooms_for_channel(channel_id)
            output = list()

            for room_id, room_name in rooms.items():
                output.append({
                    'uuid': room_id,
                    'name': room_name
                })
            return output
        except Exception as e:
            logger.error('could not list rooms: %s' % str(e))
            print(traceback.format_exc())
        return list()

    def create_room(self, room_name: str, room_id, channel_id, user_id: str) -> None:
        try:
            user_name = self.env.db.get_user_name(user_id)
            self.env.db.create_room(room_name, room_id, channel_id, user_id, user_name)
        except Exception as e:
            logger.error('could not create room: %s' % str(e))
            print(traceback.format_exc())

    def name_for_uuid(self, room_id: str) -> str:
        try:
            return self.env.db.get_room_name(room_id)
        except Exception as e:
            logger.error('could not get room name from id %s: %s' % (room_id, str(e)))
            print(traceback.format_exc())
        return ''

    def get_owners(self, room_id: str) -> dict:
        try:
            owners = self.env.db.get_owners_room(room_id)
            output = list()

            for owner_id, owner_name in owners.items():
                output.append({
                    'uuid': owner_id,
                    'name': owner_name
                })
            return output
        except Exception as e:
            logger.error('could not get room owners from id %s: %s' % (room_id, str(e)))
            print(traceback.format_exc())
        return dict()

    def get_moderators(self, room_id: str) -> dict:
        try:
            moderators = self.env.db.get_moderators_room(room_id)
            output = list()

            for moderator_id, moderator_name in moderators.items():
                output.append({
                    'uuid': moderator_id,
                    'name': moderator_name
                })
            return output
        except Exception as e:
            logger.error('could not get room moderators from id %s: %s' % (room_id, str(e)))
            print(traceback.format_exc())
        return dict()
