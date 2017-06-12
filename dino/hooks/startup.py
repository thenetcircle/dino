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

from dino import environ
from dino.config import ConfigKeys

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


class OnStartupDoneHooks(object):
    @staticmethod
    def publish_startup_done_event() -> None:
        if len(environ.env.config) == 0 or environ.env.config.get(ConfigKeys.TESTING, False):
            # assume we're testing
            return

        if environ.env.node != 'rest':
            # avoid publishing duplicate events by only letting the rest node publish external events
            return

        from uuid import uuid4 as uuid
        from datetime import datetime

        json_event = {
            'id': str(uuid()),
            'verb': 'restart',
            'content': environ.env.config.get(ConfigKeys.ENVIRONMENT),
            'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
        }

        logger.debug('publishing restart-done event to external queue: %s' % str(json_event))
        environ.env.publish(json_event, external=True)


@environ.env.observer.on('on_startup_done')
def _on_startup_done(arg) -> None:
    OnStartupDoneHooks.publish_startup_done_event()
