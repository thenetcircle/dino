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

from yapsy.IPlugin import IPlugin
from activitystreams.models.activity import Activity

from dino import utils
from dino.environ import GNEnvironment

logger = logging.getLogger()

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class OnMessageCheckBlackList(IPlugin):
    def __init__(self):
        super(OnMessageCheckBlackList, self).__init__()
        self.env = None

    def setup(self, env: GNEnvironment):
        self.env = env

    def get_black_list(self):
        return self.env.db.get_black_list()

    def _process(self, data: dict, activity: Activity):
        message = activity.object.content
        blacklist = self.get_black_list()

        if blacklist is None or len(blacklist) == 0:
            return True, None
        if message is not None and len(message) > 0:
            message = utils.b64d(message).lower()

        contains_forbidden_word = any(
            word in message
            for word in blacklist
        )

        if not contains_forbidden_word:
            return True, None

        for word in blacklist:
            if word not in message:
                continue

            logger.warning('ignoring message from user %s because a blacklisted word "%s" was used' % (activity.actor.id, word))
            return False, '"%s" is a forbidden word' % word
        return True, None

    def __call__(self, *args, **kwargs) -> (bool, str):
        data, activity = args[0], args[1]
        start = time.time()
        try:
            return self._process(data, activity)
        except Exception as e:
            logger.error('could not execute plugin check_blacklist: %s' % str(e))
            logger.exception(traceback.format_exc())
        finally:
            self.env.stats.timing('event.on_message.plugin.check_blacklist', (time.time()-start)*1000)
