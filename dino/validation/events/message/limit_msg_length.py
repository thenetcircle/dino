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


class OnMessageCheckContentLength(IPlugin):
    def __init__(self):
        super(OnMessageCheckContentLength, self).__init__()
        self.env = None
        self.enabled = False
        self.max_length = 1000

    def setup(self, env: GNEnvironment):
        self.env = env
        validation_config = self.env.config.get(ConfigKeys.VALIDATION)
        if 'on_message' not in validation_config or 'limit_msg_length' not in validation_config.get('on_message'):
            logger.info('no config enabled for plugin not_full, ignoring plugin')
            return

        on_create_config = validation_config.get('on_message').get('limit_msg_length')

        self.enabled = True
        self.max_length = on_create_config.get(ConfigKeys.MAX_MSG_LENGTH, 1000)

    def _process(self, data: dict, activity: Activity):
        message = activity.object.content
        if message is None or len(message.strip()) == 0:
            return True, None, None

        if not utils.is_base64(message):
            return False, ErrorCodes.NOT_BASE64, \
                   'invalid message content, not base64 encoded'

        message = utils.b64d(message)
        if len(message) > self.max_length:
            return False, ErrorCodes.MSG_TOO_LONG, \
                   'message content needs to be shorter than %s characters' % self.max_length

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
