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
from dino.exceptions import NoSuchRoomException

from dino import environ
from dino import utils
from dino.config import SessionKeys, UserKeys

import eventlet

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class OnLeaveHooks(object):
    @staticmethod
    def leave_room(arg: tuple) -> None:
        data, activity = arg

        # todo: should handle invisibility here? don't broadcast leaving a room if invisible
        user_id = activity.actor.id
        user_name = activity.actor.display_name
        room_id = activity.target.id

        try:
            room_name = utils.get_room_name(room_id)
        except NoSuchRoomException:
            room_name = '[removed]'

        # multi-login, can be in same room as another session
        sids = utils.sids_for_user_in_room(user_id, room_id)
        if sids is not None and len(sids) > 1:
            utils.remove_sid_for_user_in_room(user_id, room_id, environ.env.request.sid)
            return

        utils.remove_user_from_room(user_id, user_name, room_id)

        # if invisible, only send 'invisible' leave to admins in the room
        if utils.get_user_status(user_id) == UserKeys.STATUS_INVISIBLE:
            admins_in_room = environ.env.db.get_admins_in_room(room_id, user_id)
            if admins_in_room is None or len(admins_in_room) == 0:
                return

            activity_left = utils.activity_for_leave(user_id, user_name, room_id, room_name)
            for admin_id in admins_in_room:
                environ.env.out_of_scope_emit(
                    'gn_user_left', activity_left, room=admin_id, broadcast=False, namespace='/ws')
            return

        activity_left = utils.activity_for_leave(user_id, user_name, room_id, room_name)
        environ.env.emit(
            'gn_user_left', activity_left, room=room_id, broadcast=True, include_self=False, namespace='/ws')
        utils.check_if_should_remove_room(data, activity)


@environ.env.observer.on('on_leave')
def _on_leave_leave_room(arg: tuple) -> None:
    OnLeaveHooks.leave_room(arg)
