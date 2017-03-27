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
from dino.environ import GNEnvironment

logger = logging.getLogger(__name__)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class OnMessageCheckNotEmpty(IPlugin):
    def __init__(self):
        super(OnMessageCheckNotEmpty, self).__init__()
        self.env = None

    def setup(self, env: GNEnvironment):
        self.env = env

    def _process(self, data: dict, activity: Activity):
        message = activity.object.content
        if message is None or len(message.strip()) == 0 or len(utils.b64d(message).strip()) == 0:
            return False, ErrorCodes.EMPTY_MESSAGE, 'message is empty'
        return True, None, None

    def __call__(self, *args, **kwargs) -> (bool, str):
        data, activity = args[0], args[1]
        try:
            return self._process(data, activity)
        except Exception as e:
            logger.error('could not execute plugin no_empty: %s' % str(e))
            logger.exception(traceback.format_exc())
            return False, ErrorCodes.VALIDATION_ERROR, 'could not execute validation plugin no_empty'
