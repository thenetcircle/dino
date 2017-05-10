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

from activitystreams import parse as as_parser

from dino import environ
from dino.endpoint import sockets
from dino.config import ConfigKeys

from datetime import datetime
from uuid import uuid4 as uuid

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class OnKickHooks(object):
    @staticmethod
    def publish_activity(arg: tuple) -> None:
        data, activity = arg

        namespace = activity.target.url
        if namespace is None or len(namespace.strip()) == 0:
            namespace = environ.env.request.namespace

        kick_activity = {
            'actor': {
                'id': activity.actor.id,
                'displayName': activity.actor.display_name
            },
            'verb': 'kick',
            'object': {
                'id': activity.object.id,
                'displayName': activity.object.display_name
            },
            'target': {
                'url': namespace
            },
            'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
            'id': uuid()
        }

        # when banning globally, no target room is specified
        if activity.target is not None:
            kick_activity['target']['id'] = activity.target.id
            kick_activity['target']['displayName'] = activity.target.display_name

        sockets.queue_handler.handle_server_activity(data, as_parser(data))


@environ.env.observer.on('on_kick')
def _on_kick_publish_activity(arg: tuple) -> None:
    OnKickHooks.publish_activity(arg)
