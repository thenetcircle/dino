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
from dino.config import SessionKeys

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class OnJoinHooks(object):
    @staticmethod
    def join_room(arg: tuple) -> None:
        data, activity = arg

        room_id = activity.target.id
        user_id = activity.actor.id
        user_name = environ.env.session.get(SessionKeys.user_name.value)
        room_name = utils.get_room_name(room_id)

        utils.join_the_room(user_id, user_name, room_id, room_name)

    @staticmethod
    def emit_join_event(arg: tuple) -> None:
        data, activity = arg

        room_id = activity.target.id
        user_id = activity.actor.id
        room_name = utils.get_room_name(room_id)
        user_name = environ.env.session.get(SessionKeys.user_name.value)
        image = environ.env.session.get(SessionKeys.image.value, '')

        private_user_id = utils.get_private_room_for_user_id(user_id)
        activity_json = utils.activity_for_user_joined(private_user_id, user_name, room_id, room_name, image)
        environ.env.emit('gn_user_joined', activity_json, room=room_id, broadcast=True, include_self=False)

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
