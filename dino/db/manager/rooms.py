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

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class RoomManager(BaseManager):
    def __init__(self, env: GNEnvironment):
        self.env = env

    def get_rooms(self, channel_uuid):
        rooms = self.env.db.rooms_for_channel(channel_uuid)
        output = list()

        for room_id, room_name in rooms.items():
            output.append({
                'uuid': room_id,
                'name': room_name
            })
        return output

    def create_room(self, room_name: str, room_uuid, channel_id, user_id: str, user_name: str) -> None:
        self.env.db.create_room(room_name, room_uuid, channel_id, user_id, user_name)

    def name_for_uuid(self, room_uuid: str) -> str:
        return self.env.db.get_room_name(room_uuid)
