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


class ChannelManager(BaseManager):
    def __init__(self, env: GNEnvironment):
        self.env = env

    def get_channels(self) -> list:
        try:
            channels = self.env.db.get_channels()
            output = list()

            for channel_id, channel_name in channels.items():
                output.append({
                    'uuid': channel_id,
                    'name': channel_name
                })
            return output
        except Exception as e:
            logger.error('could not list channels: %s' % str(e))
            print(traceback.format_exc())

    def create_channel(self, channel_name: str, channel_id: str, user_id: str) -> None:
        try:
            self.env.db.create_channel(channel_name, channel_id, user_id)
        except Exception as e:
            logger.error('could not create channel: %s' % str(e))
            print(traceback.format_exc())
        return ''

    def name_for_uuid(self, channel_id: str) -> str:
        try:
            return self.env.db.get_channel_name(channel_id)
        except Exception as e:
            logger.error('could not get channel name from id %s: %s' % (channel_id, str(e)))
            print(traceback.format_exc())
        return ''

    def get_owners(self, channel_id: str) -> list:
        try:
            return self.env.db.get_owners_channel(channel_id)
        except Exception as e:
            logger.error('could not get channel owners from id %s: %s' % (channel_id, str(e)))
            print(traceback.format_exc())
        return list()

    def get_admins(self, channel_id: str) -> list:
        try:
            return self.env.db.get_admins_channel(channel_id)
        except Exception as e:
            logger.error('could not get channel admins from id %s: %s' % (channel_id, str(e)))
            print(traceback.format_exc())
        return list()
