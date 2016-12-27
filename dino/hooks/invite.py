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


class OnInviteHooks(object):
    @staticmethod
    def send_invite(arg: tuple) -> None:
        data, activity = arg
        invitee = activity.target.id
        invite_room = activity.actor.url
        channel_id = activity.object.url
        channel_name = activity.object.display_name
        invitee_name = activity.target.display_name

        room_name = utils.get_room_name(invite_room)

        activity_json = utils.activity_for_invite(invitee, invitee_name, invite_room, room_name, channel_id, channel_name)
        environ.env.emit('gn_invitation', activity_json, json=True, room=invitee)


@environ.env.observer.on('on_invite')
def _on_invite_send_invite(arg: tuple) -> None:
    OnInviteHooks.send_invite(arg)
