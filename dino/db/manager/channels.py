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

from typing import Union

from dino.db.manager.base import BaseManager
from dino.environ import GNEnvironment

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


class ChannelManager(BaseManager):
    def __init__(self, env: GNEnvironment):
        self.env = env

    def get_channels(self) -> list:
        channels = self.env.db.get_channels()
        output = list()

        for channel_id, (channel_name, sort_order) in channels.items():
            output.append({
                'sort': sort_order,
                'uuid': channel_id,
                'name': channel_name
            })
        return output

    def update_sort(self, channel_uuid: str, order: str):
        try:
            order = int(order)
        except Exception as e:
            logger.error('could not parser order "%s" as int: %s' % (order, str(e)))
            return 'could not parser order "%s" as int: %s' % (order, str(e))

        try:
            self.env.db.update_channel_sort_order(channel_uuid, order)
        except Exception as e:
            logger.error('could not update channel %s with order "%s" because: %s' %
                         (channel_uuid, order, str(e)))
        return None

    def remove_channel(self, channel_uuid: str) -> Union[str, None]:
        try:
            self.env.db.remove_channel(channel_uuid)
        except Exception as e:
            logger.error('could not remove channel: %s' % str(e))
            logger.exception(traceback.format_exc())
            return 'could not remove channel: %s' % str(e)
        return None

    def create_channel(self, channel_name: str, channel_id: str, user_id: str) -> Union[str, None]:
        try:
            self.env.db.create_channel(channel_name.strip(), channel_id.strip(), user_id.strip())
        except Exception as e:
            logger.error('could not create channel: %s' % str(e))
            logger.exception(traceback.format_exc())
            return 'could not create channel: %s' % str(e)
        return None

    def name_for_uuid(self, channel_id: str) -> Union[str, None]:
        try:
            return self.env.db.get_channel_name(channel_id)
        except Exception as e:
            logger.error('could not get channel name from id %s: %s' % (channel_id, str(e)))
            logger.exception(traceback.format_exc())
            return None

    def rename(self, channel_id: str, channel_name: str) -> Union[str, None]:
        try:
            self.env.db.rename_channel(channel_id, channel_name)
        except Exception as e:
            logger.error('could not rename channel with ID %s: %s' % (channel_id, str(e)))
            logger.exception(traceback.format_exc())
            return 'could not rename channel with ID %s: %s' % (channel_id, str(e))

    def get_owners(self, channel_id: str) -> Union[str, list]:
        try:
            owners = self.env.db.get_owners_channel(channel_id)
            output = list()
            for owner_id, owner_name in owners.items():
                output.append({
                    'uuid': owner_id,
                    'name': owner_name
                })
            return output
        except Exception as e:
            logger.error('could not get channel owners from id %s: %s' % (channel_id, str(e)))
            logger.exception(traceback.format_exc())
            return 'could not get channel owners from id %s: %s' % (channel_id, str(e))

    def get_admins(self, channel_id: str) -> Union[str, list]:
        try:
            admins = self.env.db.get_admins_channel(channel_id)
            output = list()

            for admin_id, admin_name in admins.items():
                output.append({
                    'uuid': admin_id,
                    'name': admin_name
                })
            return output
        except Exception as e:
            logger.error('could not get channel admins from id %s: %s' % (channel_id, str(e)))
            logger.exception(traceback.format_exc())
            return 'could not get channel admins from id %s: %s' % (channel_id, str(e))
