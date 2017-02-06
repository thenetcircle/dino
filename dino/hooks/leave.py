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


class OnLeaveHooks(object):
    @staticmethod
    def leave_room(arg: tuple) -> None:
        data, activity = arg

        #  todo: should handle invisibility here? don't broadcast leaving a room if invisible
        user_id = activity.actor.id
        user_name = environ.env.session.get(SessionKeys.user_name.value)
        room_id = activity.target.id
        room_name = utils.get_room_name(room_id)
        channel_id = utils.get_channel_for_room(room_id)

        utils.remove_user_from_room(user_id, user_name, room_id)

        activity_left = utils.activity_for_leave(user_id, user_name, room_id, room_name)
        environ.env.emit('gn_user_left', activity_left, room=room_id, broadcast=True, include_self=False)

        # todo: can we do this async? let the request finish, as this might take a while for larger rooms
        # todo: move this to a plugin, use yapsy to inject
        if not environ.env.db.is_room_ephemeral(room_id) or not utils.is_owner(room_id, user_id):
            return

        owners = utils.get_owners_for_room(room_id)
        users_in_room = utils.get_users_in_room(room_id)

        if user_id in users_in_room:
            del users_in_room[user_id]

        for owner_id, _ in owners.items():
            if owner_id in users_in_room:
                # don't remove the room if an owner is still in the room
                return

        environ.env.db.remove_room(channel_id, room_id)

        for user_id_still_in_room, user_name_still_in_room in users_in_room.items():
            kick_activity = {
                'actor': {
                    'id': user_id,
                    'displayName': utils.b64e(user_name)
                },
                'verb': 'kick',
                'object': {
                    'id': user_id_still_in_room,
                    'displayName': utils.b64e(user_name_still_in_room),
                    'content': utils.b64e('All owners have left the room')
                },
                'target': {
                    'url': environ.env.request.namespace,
                    'id': room_id,
                    'displayName': utils.b64e(room_name)
                }
            }
            environ.env.publish(kick_activity)

        remove_activity = utils.activity_for_remove_room(user_id, user_name, room_id, room_name)
        environ.env.emit('gn_room_removed', remove_activity, broadcast=True, include_self=True)


@environ.env.observer.on('on_leave')
def _on_leave_leave_room(arg: tuple) -> None:
    OnLeaveHooks.leave_room(arg)
