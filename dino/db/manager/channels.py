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


class ChannelManager(BaseManager):
    def __init__(self, env: GNEnvironment):
        self.env = env

    def get_channels(self) -> list:
        channels = self.env.db.get_channels()
        output = list()

        for channel_id, channel_name in channels.items():
            output.append({
                'uuid': channel_id,
                'name': channel_name
            })
        return output

    def create_channel(self, channel_name: str, channel_id: str, user_id: str) -> None:
        self.env.db.create_channel(channel_name, channel_id, user_id)

    def name_for_uuid(self, channel_uuid: str) -> str:
        return self.env.db.get_channel_name(channel_uuid)
