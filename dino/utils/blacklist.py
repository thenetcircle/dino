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
    def __init__(self, env):
        self.env = env

    def _get_black_list(self):
        # cached in db object
        return self.env.db.get_black_list()

    def _contains_blacklisted_word(self, activity: Activity):
        message = activity.object.content
        blacklist = self._get_black_list()

        if blacklist is None or len(blacklist) == 0:
            return False
        if message is not None and len(message) > 0:
            message = utils.b64d(message).lower()

        contains_forbidden_word = any(
            word in message
            for word in blacklist
        )

        if not contains_forbidden_word:
            return False

        for word in blacklist:
            if word not in message:
                continue

            blacklist_activity = utils.activity_for_blacklisted_word(activity, word)
            self.env.publish(blacklist_activity)
            logger.warning('message from user %s used a blacklisted word "%s"' % (activity.actor.id, word))
            return True
        return False

    def contains_blacklisted_word(self, activity: Activity) -> (bool, str):
        start = time.time()
        try:
            return self._contains_blacklisted_word(activity)
        except Exception as e:
            logger.error('could not check blacklist: %s' % str(e))
            logger.exception(traceback.format_exc())
        finally:
            self.env.stats.timing('event.on_message.check_blacklist', (time.time()-start)*1000)
        return False
