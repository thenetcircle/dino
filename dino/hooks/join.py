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
import eventlet

from dino import environ
from dino import utils
from dino.config import SessionKeys
from dino.config import UserKeys
from dino.utils.decorators import timeit

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


class OnJoinHooks(object):
    @staticmethod
    @timeit(logger, 'on_join_hook_join_room')
    def join_room(arg: tuple) -> None:
        data, activity = arg
        room_id = activity.target.id
        user_id = activity.actor.id

        user_name = environ.env.session.get(SessionKeys.user_name.value)
        room_name = utils.get_room_name(room_id)

        utils.join_the_room(user_id, user_name, room_id, room_name)

    @staticmethod
    @timeit(logger, 'on_join_hook_emit_join_event')
    def emit_join_event(activity, user_id, user_name, image) -> None:
        room_id = activity.target.id
        room_name = utils.get_room_name(room_id)

        # if invisible, only sent 'invisible' join to admins in the room
        if utils.get_user_status(user_id) == UserKeys.STATUS_INVISIBLE:
            admins_in_room = environ.env.db.get_admins_in_room(room_id, user_id)
            if admins_in_room is None or len(admins_in_room) == 0:
                return

            room_name = utils.get_room_name(room_id)
            activity_json = utils.activity_for_user_joined_invisibly(user_id, user_name, room_id, room_name, image)
            for admin_id in admins_in_room:
                environ.env.out_of_scope_emit('gn_user_joined', activity_json, room=admin_id, broadcast=False)
            return

        activity_json = utils.activity_for_user_joined(user_id, user_name, room_id, room_name, image)
        environ.env.out_of_scope_emit('gn_user_joined', activity_json, room=room_id, broadcast=True, include_self=False)
        environ.env.publish(activity_json)


@environ.env.observer.on('on_join')
def _on_join_join_room(arg: tuple) -> None:
    OnJoinHooks.join_room(arg)


@environ.env.observer.on('on_join')
def _on_join_emit_join_event(arg: tuple) -> None:
    user_name = environ.env.session.get(SessionKeys.user_name.value)
    user_id = environ.env.session.get(SessionKeys.user_id.value)
    image = environ.env.session.get(SessionKeys.image.value, '')
    eventlet.spawn(OnJoinHooks.emit_join_event, arg[1], user_id, user_name, image)
