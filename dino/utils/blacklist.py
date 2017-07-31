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
import time

from activitystreams.models.activity import Activity

from dino import utils

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


class BlackListChecker(object):
    """
    Check if a blacklisted word is used in a message. Here the check is implemented in this way:

        contains_forbidden_word = any(
            word in message
            for word in blacklist
        )

    ...since a blacklisted work, e.g. 'the donald', might be blacklisted, but individual words like 'the' and 'donald'
    might not be. So the following (faster) way:

        contains_forbidden_word = any(
            word in blacklist
            for word in message.split()
        )
        if not contains_forbidden_word:
            return None

    ...shouldn't be done here. On the other hand it can help as a 'shortcut' if the blacklist is large enough, e.g.:

        contains_partly_forbidden_word = any(
            word in blacklist
            for word in message.split()
        )
        if not contains_partly_forbidden_word:
            return None

    ...and then do the full, slower check:

        contains_real_forbidden_word = any(
            word in message
            for word in blacklist
        )
        if not contains_real_forbidden_word:
            return None

    Since if 'the donald' is blocked, then so would 'donald'. So if 'donald' matches then we can check if 'the donald'
    matches'.

    The first partial check is around 20x faster in tests. Cuckoo filters weren't really effective until blacklist size
    exceeded ~60k entries:

        length of blacklist: 60000, messages to check: 1000000, word length: 25487
        [cuckoo] done in 24.35s, avg time: 0.0243ms
        [regular] done in 82.57s, avg time: 0.0826ms
        [partial] done in 3.34s, avg time: 0.0033ms
    """

    def __init__(self, env):
        self.env = env

    def _get_black_list(self):
        # cached in db object
        return self.env.db.get_black_list()

    def _contains_blacklisted_word(self, activity: Activity):
        message = activity.object.content
        blacklist = self._get_black_list()

        if blacklist is None or len(blacklist) == 0:
            return None
        if message is not None and len(message) > 0:
            message = utils.b64d(message).lower()

        contains_forbidden_word = any(
            word in message
            for word in blacklist
        )

        if not contains_forbidden_word:
            return None

        for word in blacklist:
            if word not in message:
                continue

            logger.warning('message from user %s used a blacklisted word "%s"' % (activity.actor.id, word))
            return word
        return None

    def contains_blacklisted_word(self, activity: Activity) -> (bool, str):
        start = time.time()
        try:
            return self._contains_blacklisted_word(activity)
        except Exception as e:
            logger.error('could not check blacklist: %s' % str(e))
            logger.exception(traceback.format_exc())
        finally:
            self.env.stats.timing('event.on_message.check_blacklist', (time.time()-start)*1000)
        return None
