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
import logging

from dino import utils
from dino.db.manager.base import BaseManager
from dino.environ import GNEnvironment
from dino.exceptions import RoomNameExistsForChannelException

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


class RoomManager(BaseManager):
    def __init__(self, env: GNEnvironment):
        self.env = env

    def get_rooms(self, channel_id: str) -> list:
        rooms = self.env.db.rooms_for_channel(channel_id)
        default_rooms = self.env.db.get_default_rooms() or set()
        output = list()

        for room_id, room_details in rooms.items():
            room_name = room_details['name']
            output.append({
                'uuid': room_id,
                'sort': room_details['sort_order'],
                'ïs_admin': room_details['admin'],
                'is_default': room_id in default_rooms,
                'is_ephemeral': room_details['ephemeral'],
                'name': room_name
            })
        return output

    def update_sort(self, room_uuid: str, order: str):
        try:
            order = int(order)
        except Exception as e:
            logger.error('could not parser order "%s" as int: %s' % (order, str(e)))
            return 'could not parser order "%s" as int: %s' % (order, str(e))

        try:
            self.env.db.update_room_sort_order(room_uuid, order)
        except Exception as e:
            logger.error('could not update room %s with order "%s" because: %s' %
                         (room_uuid, order, str(e)))
        return None

    def set_ephemeral_room(self, room_id: str) -> None:
        self.env.db.set_ephemeral_room(room_id)

    def unset_ephemeral_room(self, room_id: str) -> None:
        self.env.db.unset_ephemeral_room(room_id)

    def set_admin_room(self, room_id: str) -> None:
        self.env.db.set_admin_room(room_id)

    def unset_admin_room(self, room_id: str) -> None:
        self.env.db.unset_admin_room(room_id)

    def set_default_room(self, room_id: str) -> None:
        self.env.db.add_default_room(room_id)

    def unset_default_room(self, room_id: str) -> None:
        self.env.db.remove_default_room(room_id)

    def create_room(self, room_name: str, room_id: str, channel_id: str, user_id: str) -> Union[str, None]:
        if room_name is None or len(room_name.strip()) == 0:
            return 'empty room name'
        if user_id is None or len(user_id.strip()) == 0:
            return 'empty user id'
        if channel_id is None or len(channel_id.strip()) == 0:
            return 'empty channel id'
        if room_id is None or len(room_id.strip()) == 0:
            return 'empty room id'

        user_id = user_id.strip()
        user_name = str(self.env.db.get_user_name(user_id)).strip()
        room_name = str(room_name).strip()
        room_id = str(room_id).strip()
        channel_id = str(channel_id).strip()
        user_id = str(user_id).strip()

        self.env.db.create_room(room_name, room_id, channel_id, user_id, user_name, ephemeral=False, sort_order=10)
        return None

    def remove_room(self, channel_id: str, room_id: str) -> None:
        room_name = self.env.db.get_room_name(room_id)
        remove_activity = utils.activity_for_remove_room('0', 'admin', room_id, room_name)
        self.env.db.remove_room(channel_id, room_id)
        self.env.publish(remove_activity)

    def rename(self, channel_id: str, room_id: str, room_name: str) -> Union[str, None]:
        try:
            return self.env.db.rename_room(channel_id, room_id, room_name)
        except RoomNameExistsForChannelException:
            return 'room name already exists'
        except Exception as e:
            logger.error('could not rename room with ID %s: %s' % (room_id, str(e)))
            return 'could not rename room with ID %s: %s' % (room_id, str(e))

    def name_for_uuid(self, room_id: str) -> str:
        try:
            return self.env.db.get_room_name(room_id)
        except Exception as e:
            logger.error('could not get room name from id %s: %s' % (room_id, str(e)))
        return None

    def get_owners(self, room_id: str) -> list:
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
            return 'could not get room owners from id %s: %s' % (room_id, str(e))

    def get_moderators(self, room_id: str) -> list:
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
            return 'could not get room moderators from id %s: %s' % (room_id, str(e))
