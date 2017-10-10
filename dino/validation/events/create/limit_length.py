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


class OnCreateCheckNameLength(IPlugin):
    def __init__(self):
        super(OnCreateCheckNameLength, self).__init__()
        self.env = None
        self.enabled = False
        self.min_length = 3
        self.max_length = 120

    def setup(self, env: GNEnvironment):
        self.env = env
        try:
            on_create_config = self.env.config.get(ConfigKeys.VALIDATION).get('on_create').get('limit_length')
        except Exception:
            logger.info('no config enabled for plugin not_full, ignoring plugin')
            return

        self.enabled = True
        self.min_length = on_create_config.get(ConfigKeys.MAX_USERS_LOW, 3)
        self.max_length = on_create_config.get(ConfigKeys.MAX_USERS_HIGH, 120)

    def _process(self, data: dict, activity: Activity):
        room_name = activity.target.display_name

        if room_name is None or room_name.strip() == '':
            return False, ErrorCodes.MISSING_TARGET_DISPLAY_NAME, \
                   'got blank room name, can not create'

        if not utils.is_base64(room_name):
            return False, ErrorCodes.NOT_BASE64, \
                   'invalid room name, not base64 encoded'

        room_name = utils.b64d(room_name)

        if len(room_name) < self.min_length:
            return False, ErrorCodes.ROOM_NAME_TOO_SHORT, \
                   'room name needs to be longer than %s characters' % self.min_length

        if len(room_name) > self.max_length:
            return False, ErrorCodes.ROOM_NAME_TOO_LONG, \
                   'room name needs to be shorter than %s characters' % self.max_length

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
