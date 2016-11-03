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


class AclManager(BaseManager):
    def __init__(self, env: GNEnvironment):
        self.env = env

    def get_acls_channel(self, channel_id: str) -> list:
        acls = self.env.db.get_all_acls_channel(channel_id)
        return self._format_acls(acls)

    def get_acls_room(self, room_id: str) -> list:
        acls = self.env.db.get_all_acls_room(room_id)
        return self._format_acls(acls)

    def delete_acl_channel(self, channel_id: str, action: str, acl_type: str) -> None:
        self.env.db.delete_acl_in_channel_for_action(channel_id, acl_type, action)

    def update_channel_acl(self, channel_id: str, action: str, acl_type: str, acl_value: str) -> None:
        self.env.db.update_acl_in_channel_for_action(channel_id, action, acl_type, acl_value)

    def update_room_acl(self, channel_id: str, room_id: str, action: str, acl_type: str, acl_value: str) -> None:
        self.env.db.update_acl_in_room_for_action(channel_id, room_id, action, acl_type, acl_value)

    def delete_acl_room(self, room_id: str, action: str, acl_type: str) -> None:
        self.env.db.delete_acl_in_room_for_action(room_id, acl_type, action)

    def add_acl_channel(self, channel_id: str, action: str, acl_type: str, acl_value: str) -> None:
        self.env.db.add_acls_in_channel_for_action(channel_id, action, {acl_type: acl_value})

    def add_acl_room(self, room_id: str, action: str, acl_type: str, acl_value: str) -> None:
        self.env.db.add_acls_in_room_for_action(room_id, action, {acl_type: acl_value})

    def _format_acls(self, all_acls: dict) -> list:
        output = list()
        for action, acls in all_acls.items():
            for acl_type, acl_value in acls.items():
                output.append({
                    'action': action,
                    'type': acl_type,
                    'value': acl_value
                })
        return output
