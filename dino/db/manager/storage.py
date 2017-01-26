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
from dino.utils import b64e

import logging

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


class StorageManager(BaseManager):
    def __init__(self, env: GNEnvironment):
        self.env = env

    def get_undeleted_messages_for_user(self, user_id: str) -> list:
        return self.env.storage.get_undeleted_message_ids_for_user(user_id)

    def undelete_message(self, message_id: str) -> None:
        self.env.storage.undelete_message(message_id)

    def delete_message(self, message_id: str) -> None:
        self.env.storage.delete_message(message_id)

    def find_history(self, room_id, user_id, from_time, to_time):
        if from_time is None or to_time is None:
            return

        from_time = int(from_time.strftime('%s'))
        to_time = int(to_time.strftime('%s'))
        return self.env.storage.get_history_for_time_slice(room_id, user_id, from_time, to_time)
