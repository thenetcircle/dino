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
from dino.environ import GNEnvironment

logger = logging.getLogger(__name__)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class OnLoginEnforceSingleSession(IPlugin):
    def __init__(self):
        super(OnLoginEnforceSingleSession, self).__init__()
        self.env = None
        self.enabled = False

    def setup(self, env: GNEnvironment):
        self.env = env
        self.enabled = not utils.is_multiple_sessions_allowed()

        if not self.enabled:
            logger.info('no config enabled for plugin single_session, ignoring plugin')

    def _process(self, data: dict, activity: Activity):
        user_id = activity.actor.id
        user_name = activity.actor.display_name

        if not self.env.config.get(ConfigKeys.TESTING):
            if str(user_id) in self.env.connected_user_ids:
                logger.info('a new connection for user ID %s, will disconnect previous one' % user_id)
                previous_sid = self.env.connected_user_ids[str(user_id)]
                disconnect_act = utils.activity_for_disconnect(user_id, user_name)
                self.env.emit('gn_disconnect', disconnect_act, room=previous_sid)
                self.env.disconnect_by_sid(self.env.connected_user_ids[str(user_id)])
            self.env.connected_user_ids[str(user_id)] = self.env.request.sid

        return True, None, None

    def __call__(self, *args, **kwargs) -> (bool, str):
        if not self.enabled:
            return

        data, activity = args[0], args[1]
        try:
            return self._process(data, activity)
        except Exception as e:
            logger.error('could not execute plugin single_session: %s' % str(e))
            logger.exception(traceback.format_exc())
            return False, ErrorCodes.VALIDATION_ERROR, 'could not execute validation plugin single_session'
