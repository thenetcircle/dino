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


class OnStatusHooks(object):
    @staticmethod
    def set_status(arg: tuple) -> None:
        data, activity = arg

        user_id = activity.actor.id
        user_name = environ.env.session.get(SessionKeys.user_name.value, None)
        image = environ.env.session.get(SessionKeys.image.value, '')
        status = activity.verb

        if status == 'online':
            environ.env.db.set_user_online(user_id)
            rooms = utils.rooms_for_user(user_id)
            for room_id in rooms:
                room_name = utils.get_room_name(room_id)
                activity_json = utils.activity_for_user_joined(user_id, user_name, room_id, room_name, image)
                environ.env.emit('gn_user_joined', activity_json, room=room_id, broadcast=True, include_self=False)

        elif status == 'invisible':
            environ.env.db.set_user_invisible(user_id)
            activity_json = utils.activity_for_disconnect(user_id, user_name)
            environ.env.emit('gn_user_disconnected', activity_json, broadcast=True, include_self=False)

            rooms = utils.rooms_for_user(user_id)
            for room_id in rooms:
                admins_in_room = environ.env.db.get_admins_in_room(room_id)
                if admins_in_room is None or len(admins_in_room) == 0:
                    continue

                room_name = utils.get_room_name(room_id)
                activity_json = utils.activity_for_user_joined_invisibly(user_id, user_name, room_id, room_name, image)
                for admin_id in admins_in_room:
                    environ.env.emit('gn_user_joined', activity_json, room=admin_id, broadcast=False)

        elif status == 'offline':
            environ.env.db.set_user_offline(user_id)
            activity_json = utils.activity_for_disconnect(user_id, user_name)
            environ.env.emit('gn_user_disconnected', activity_json, broadcast=True, include_self=False)


@environ.env.observer.on('on_status')
def _on_status_set_status(arg: tuple) -> None:
    OnStatusHooks.set_status(arg)
