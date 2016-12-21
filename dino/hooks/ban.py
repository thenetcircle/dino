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
from dino import utils

logger = logging.getLogger(__name__)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class OnBanHooks(object):
    @staticmethod
    def ban_user(arg: tuple) -> None:
        data, activity = arg
        room_id = activity.target.id
        kicked_id = activity.object.id
        ban_duration = activity.object.summary
        # TODO: this ban could be for room, channel or globally

        try:
            utils.ban_user(room_id, kicked_id, ban_duration)
        except Exception as e:
            logger.exception('could not ban user, should have been caught in validator: %s' % str(e))
            logger.error('request activity for failed ban was: %s' % str(data))

    @staticmethod
    def emit_ban_event(arg: tuple) -> None:
        data, activity = arg

        ban_activity = {
            'actor': {
                'id': activity.actor.id,
                'displayName': activity.actor.display_name
            },
            'verb': 'ban',
            'object': {
                'id': activity.object.id,
                'displayName': activity.object.display_name
            }
        }

        reason = None
        if activity.object is not None:
            reason = activity.object.content
        if reason is not None and len(reason.strip()) > 0:
            ban_activity['object']['content'] = reason

        # when banning globally, not target room is specified
        if activity.target is not None:
            ban_activity['target'] = dict()
            ban_activity['target']['id'] = activity.target.id
            ban_activity['target']['displayName'] = activity.target.display_name

        environ.env.publish(ban_activity, external=True)


@environ.env.observer.on('on_ban')
def _on_ban_ban_user(arg: tuple) -> None:
    OnBanHooks.ban_user(arg)


@environ.env.observer.on('on_ban')
def _on_ban_emit_external_event(arg: tuple) -> None:
    OnBanHooks.emit_ban_event(arg)
