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

from dino import environ
from dino import utils

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class OnKickHooks(object):
    @staticmethod
    def remove_from_room(arg: tuple) -> None:
        data, activity = arg
        room_id = activity.target.id
        user_id = activity.object.id
        utils.kick_user(room_id, user_id)

    @staticmethod
    def publish_activity(arg: tuple) -> None:
        data, activity = arg

        namespace = activity.target.url
        if namespace is None or len(namespace.strip()) == 0:
            namespace = environ.env.request.namespace

        kick_activity = {
            'actor': {
                'id': activity.actor.id,
                'summary': activity.actor.summary
            },
            'verb': 'kick',
            'object': {
                'id': activity.object.id,
                'summary': activity.object.summary
            },
            'target': {
                'url': namespace
            }
        }

        # when banning globally, not target room is specified
        if activity.target is not None:
            kick_activity['target']['id'] = activity.target.id
            kick_activity['target']['displayName'] = activity.target.display_name

        environ.env.publish(kick_activity)

    @staticmethod
    def emit_kick_event(arg: tuple) -> None:
        data, activity = arg

        kick_activity = {
            'actor': {
                'id': activity.actor.id,
                'displayName': activity.actor.display_name
            },
            'verb': 'kick',
            'object': {
                'id': activity.object.id,
                'displayName': activity.object.display_name
            }
        }

        reason = None
        if activity.object is not None:
            reason = activity.object.content
        if reason is not None and len(reason.strip()) > 0:
            kick_activity['object']['content'] = reason

        # when banning globally, not target room is specified
        if activity.target is not None:
            kick_activity['target'] = dict()
            kick_activity['target']['id'] = activity.target.id
            kick_activity['target']['displayName'] = activity.target.display_name

        environ.env.publish(kick_activity, external=True)


@environ.env.observer.on('on_kick')
def _on_kick_remove_from_room(arg: tuple) -> None:
    OnKickHooks.remove_from_room(arg)


@environ.env.observer.on('on_kick')
def _on_kick_publish_activity(arg: tuple) -> None:
    OnKickHooks.publish_activity(arg)


@environ.env.observer.on('on_kick')
def _on_kick_emit_event(arg: tuple) -> None:
    OnKickHooks.emit_kick_event(arg)
