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
        super().__init__(env)

    def get_all_spam_from_user(self, user_id: str) -> list:
        return self.env.db.get_spam_from(user_id)

    def get_latest_spam(self, limit=500) -> list:
        return self.env.db.get_latest_spam(limit)

    def get_spam(self, spam_id: int) -> dict:
        return self.env.db.get_spam(spam_id)

    def is_enabled(self) -> bool:
        return self.env.service_config.is_spam_classifier_enabled()

    def disable(self):
        self.env.db.disable_spam_classifier()
        self.env.service_config.reload()

    def set_settings(self, enabled, max_length, min_length, should_delete, should_save, threshold, ignore_emoji):
        if should_save is not None:
            max_length = int(max_length)

        if should_save is not None:
            min_length = int(min_length)

        if threshold is not None:
            threshold = int(threshold)
            if threshold < 50 or threshold > 99:
                raise ValueError('threshold needs to be between 50 and 99 (inclusive)')

        if ignore_emoji is not None:
            ignore_emoji = True if ignore_emoji in {True, '1', 'true', 'True', 'yes'} else False

        if enabled is not None:
            enabled = True if enabled in {True, '1', 'true', 'True', 'yes'} else False

        if should_save is not None:
            should_save = True if should_save in {True, '1', 'true', 'True', 'yes'} else False

        if should_delete is not None:
            should_delete = True if should_delete in {True, '1', 'true', 'True', 'yes'} else False

        self.env.db.update_spam_config(
            enabled, max_length, min_length,
            should_delete, should_save, threshold, ignore_emoji
        )
        self.env.service_config.reload()

    def get_settings(self):
        return self.env.service_config.get_config()

    def enable(self):
        self.env.db.enable_spam_classifier()
        self.env.service_config.reload()

    def set_min_length(self, min_length):
        self.env.db.set_spam_min_length(min_length)
        self.env.service_config.reload()

    def find(self, room_id, user_id, from_time, to_time) -> (list, datetime, datetime):
        if is_blank(user_id) and is_blank(room_id):
            raise RuntimeError('need user ID and/or room ID')

        from_time, to_time = self.format_time_range(from_time, to_time)
        from_time_int = int(from_time.strftime('%s'))
        to_time_int = int(to_time.strftime('%s'))

        from_time = from_time.strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
        to_time = to_time.strftime(ConfigKeys.DEFAULT_DATE_FORMAT)

        history = self.env.db.get_spam_for_time_slice(
            room_id, user_id, from_time_int, to_time_int)

        return history, from_time, to_time

    def set_correct_or_not(self, spam_id: int, correct_or_not: bool):
        self.env.db.set_spam_correct_or_not(spam_id, correct_or_not)
