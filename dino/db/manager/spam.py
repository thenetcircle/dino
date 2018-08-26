import datetime
import logging

from dino.config import ConfigKeys
from dino.db.manager import StorageManager
from dino.environ import GNEnvironment

logger = logging.getLogger(__name__)


def is_blank(s: str):
    return s is None or len(s.strip()) == 0


class SpamManager(StorageManager):
    def __init__(self, env: GNEnvironment):
        super(StorageManager).__init__(env)

    def get_all_spam_from_user(self, user_id: str) -> list:
        return self.env.db.get_spam_from(user_id)

    def find(self, room_id, user_id, from_time, to_time) -> (list, datetime, datetime):
        if is_blank(user_id) and is_blank(room_id):
            raise RuntimeError('need user ID and/or room ID')

        from_time_int, to_time_int = self.format_time_range(from_time, to_time)
        from_time = datetime.datetime.fromtimestamp(from_time_int).strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
        to_time = datetime.datetime.fromtimestamp(to_time_int).strftime(ConfigKeys.DEFAULT_DATE_FORMAT)

        return self.env.db.get_spam_for_time_slice(
            room_id, user_id, from_time_int, to_time_int), from_time, to_time

    def set_correct_or_not(self, spam_id: int, correct_or_not: bool):
        self.env.db.set_spam_correct_or_not(spam_id, correct_or_not)
