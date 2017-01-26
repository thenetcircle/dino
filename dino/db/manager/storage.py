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

from dateutil import parser
from dateutil.tz import tzutc

import datetime
import logging

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


def is_blank(s: str):
    return s is None or len(s.strip()) == 0


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
        if is_blank(user_id) and is_blank(room_id):
            raise RuntimeError('need user ID and/or room ID')

        if not is_blank(from_time):
            try:
                from_time = parser.parse(from_time).astimezone(tzutc())
            except Exception as e:
                logger.error('invalid from time "%s": %s' % (str(from_time), str(e)))
                raise RuntimeError('invalid from time "%s"' % str(from_time))
        else:
            from_time = None

        if not is_blank(to_time):
            try:
                to_time = parser.parse(to_time).astimezone(tzutc())
            except Exception as e:
                logger.error('invalid to time "%s": %s' % (str(to_time), str(e)))
                raise RuntimeError('invalid to time "%s": %s' % str(to_time))
        else:
            to_time = None

        if from_time is not None and to_time is not None:
            if from_time > to_time:
                logger.error('from time %s must be before to time %s' % (str(from_time), str(to_time)))
                raise RuntimeError('from time %s must be before to time %s' % (str(from_time), str(to_time)))

        if to_time is not None and from_time is None:
            from_time = to_time - datetime.timedelta(seconds=60*60)
        if from_time is not None and to_time is None:
            to_time = from_time + datetime.timedelta(seconds=60*60)

        if from_time is not None and to_time is not None:
            if to_time - from_time > datetime.timedelta(days=7):
                to_time = from_time + datetime.timedelta(days=7)

        if from_time is None or to_time is None:
            to_time = datetime.datetime.utcnow()
            from_time = to_time - datetime.timedelta(days=7)

        from_time = int(from_time.strftime('%s'))
        to_time = int(to_time.strftime('%s'))
        return self.env.storage.get_history_for_time_slice(room_id, user_id, from_time, to_time)
