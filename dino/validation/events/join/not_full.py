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
from yapsy.IPlugin import IPlugin
from activitystreams.models.activity import Activity

from dino import utils
from dino.config import ErrorCodes
from dino.config import ConfigKeys
from dino.config import SessionKeys
from dino.environ import GNEnvironment

logger = logging.getLogger(__name__)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class OnJoinCheckNotFull(IPlugin):
    def __init__(self):
        super(OnJoinCheckNotFull, self).__init__()
        self.env = None
        self.enabled = False

    def setup(self, env: GNEnvironment):
        self.env = env
        try:
            on_join_config = self.env.config.get(ConfigKeys.VALIDATION).get('on_join').get('not_full')
        except KeyError:
            logger.info('no config enabled for plugin not_full, ignoring plugin')
            return

        self.enabled = True
        self.max_users_low = on_join_config.get(ConfigKeys.MAX_USERS_LOW, 100)
        self.max_users_high = on_join_config.get(ConfigKeys.MAX_USERS_HIGH, 120)
        self.max_users_exception = on_join_config.get(ConfigKeys.MAX_USERS_EXCEPTION, '').split(',')

    def _process(self, data: dict, activity: Activity):
        room_id = activity.target.id
        user_id = activity.actor.id

        if utils.is_super_user(user_id):
            return True, None, None

        n_users = len(utils.get_users_in_room(room_id))
        membership = self.env.session.get(SessionKeys.membership.value, '')

        if n_users < self.max_users_low:
            return True, None, None
        if n_users > self.max_users_high:
            return False, ErrorCodes.ROOM_FULL, 'room is full'

        if len(membership.strip()) == 0 or membership not in self.max_users_exception:
            return False, ErrorCodes.ROOM_FULL, 'room is full'

        return True, None, None

    def __call__(self, *args, **kwargs) -> (bool, str):
        if not self.enabled:
            return

        data, activity = args[0], args[1]
        try:
            return self._process(data, activity)
        except Exception as e:
            logger.error('could not execute plugin not_full: %s' % str(e))
            logger.exception(traceback.format_exc())
            return False, ErrorCodes.VALIDATION_ERROR, 'could not execute validation plugin not_full'
