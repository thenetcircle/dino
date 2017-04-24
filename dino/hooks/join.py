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
from dino.config import SessionKeys
from dino.config import UserKeys

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


class OnJoinHooks(object):
    @staticmethod
    def join_room(arg: tuple) -> None:
        data, activity = arg
        room_id = activity.target.id
        user_id = activity.actor.id

        user_name = environ.env.session.get(SessionKeys.user_name.value)
        room_name = utils.get_room_name(room_id)

        if not utils.user_is_online(user_id):
            logger.warn('user "%s" (%s) is not online, not joining room "%s" (%s)!' %
                        (user_name, user_id, room_name, room_id))
            return

        utils.join_the_room(user_id, user_name, room_id, room_name)

    @staticmethod
    def emit_join_event(arg: tuple) -> None:
        data, activity = arg
        room_id = activity.target.id
        user_id = activity.actor.id

        # don't send the gn_user_joined event if this user is invisible
        if utils.get_user_status(user_id) == UserKeys.STATUS_INVISIBLE:
            return

        room_name = utils.get_room_name(room_id)
        user_name = environ.env.session.get(SessionKeys.user_name.value)

        if not utils.user_is_online(user_id):
            logger.warn('user "%s" (%s) is not online, not emitting join event to room "%s" (%s)!' %
                        (user_name, user_id, room_name, room_id))
            return

        image = environ.env.session.get(SessionKeys.image.value, '')

        activity_json = utils.activity_for_user_joined(user_id, user_name, room_id, room_name, image)
        environ.env.emit('gn_user_joined', activity_json, room=room_id, broadcast=True, include_self=False)
        environ.env.publish(activity_json, external=True)

    @staticmethod
    def set_sid_for_user(arg: tuple) -> None:
        data, activity = arg
        user_id = activity.actor.id
        utils.set_sid_for_user_id(user_id, environ.env.request.sid)


@environ.env.observer.on('on_join')
def _on_join_join_room(arg: tuple) -> None:
    OnJoinHooks.join_room(arg)


@environ.env.observer.on('on_join')
def _on_join_set_sid_for_user(arg: tuple) -> None:
    OnJoinHooks.set_sid_for_user(arg)


@environ.env.observer.on('on_join')
def _on_join_emit_join_event(arg: tuple) -> None:
    OnJoinHooks.emit_join_event(arg)
