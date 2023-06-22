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
from dino.config import ConfigKeys
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

    def get_all_message_ids_from_user(self, user_id: str, include_deleted: bool = False) -> list:
        if include_deleted:
            return self.env.storage.get_all_message_ids_for_user(user_id)
        else:
            return self.env.storage.get_undeleted_message_ids_for_user(user_id)

    def get_all_messages_from_user(self, user_id: str, from_time: str=None, to_time: str=None) -> list:
        from_time, to_time = self.format_time_range(from_time, to_time)

        if from_time is not None and to_time is not None:
            from_time_int = int(from_time.strftime('%s'))
            to_time_int = int(to_time.strftime('%s'))
            return self.env.storage.get_undeleted_messages_for_user_and_time(
                user_id, from_time_int, to_time_int)

        msg_ids = self.env.storage.get_undeleted_message_ids_for_user(user_id)
        return self.env.storage.get_messages(msg_ids)

    def undelete_message(self, message_id: str) -> None:
        self.env.storage.undelete_message(message_id)
        self.env.db.mark_spam_not_deleted_if_exists(message_id)

    def delete_message(self, message_id: str, clear_body: bool = True) -> None:
        self.env.storage.delete_message(message_id, clear_body=clear_body)
        self.env.db.mark_spam_deleted_if_exists(message_id)

    def delete_messages(self, message_ids: list, clear_body: bool = True) -> None:
        self.env.storage.delete_messages(message_ids, clear_body=clear_body)
        self.env.db.mark_spams_deleted_if_exists(message_ids)

    def get_latest_messages(self, target_id: str, limit: int = 100):
        return self.env.storage.get_history(target_id, limit)

    def paginate_history(self, room_id, to_time, limit: int):
        try:
            to_time = parser.parse(to_time).astimezone(tzutc())
            to_time_int = int(to_time.strftime('%s'))
        except Exception as e:
            logger.error('invalid to time "%s": %s' % (str(to_time), str(e)))
            raise RuntimeError('invalid to time "%s": %s' % (str(to_time), str(e)))

        if limit <= 0:
            raise RuntimeError("limit needs to be >0 but was '{}'".format(limit))

        return self.env.storage.get_history_pagination(
            room_id, to_time_int, limit
        )

    def find_history(self, room_id, user_id, from_time, to_time) -> (list, datetime, datetime):
        if is_blank(user_id) and is_blank(room_id):
            raise RuntimeError('need user ID and/or room ID')

        from_time, to_time = self.format_time_range(from_time, to_time)
        from_time_int = int(from_time.strftime('%s'))
        to_time_int = int(to_time.strftime('%s'))

        from_time = from_time.strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
        to_time = to_time.strftime(ConfigKeys.DEFAULT_DATE_FORMAT)

        history = self.env.storage.get_history_for_time_slice(
            room_id, user_id, from_time_int, to_time_int)

        return history, from_time, to_time

    def format_time_range(self, from_time: str=None, to_time: str=None):
        if not is_blank(from_time):
            try:
                from_time = parser.parse(from_time).astimezone(tzutc())
            except Exception as e:
                logger.error('invalid from time "%s": %s' % (str(from_time), str(e)))
                raise RuntimeError('invalid from time "%s": %s' % (str(to_time), str(e)))
        else:
            from_time = None

        if not is_blank(to_time):
            try:
                to_time = parser.parse(to_time).astimezone(tzutc())
            except Exception as e:
                logger.error('invalid to time "%s": %s' % (str(to_time), str(e)))
                raise RuntimeError('invalid to time "%s": %s' % (str(to_time), str(e)))
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

        if from_time is None or to_time is None:
            to_time = datetime.datetime.utcnow()
            from_time = to_time - datetime.timedelta(days=7)

        return from_time, to_time
