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


class OnRequestAdminHooks(object):
    @staticmethod
    def send_request(arg: tuple) -> None:
        data, activity = arg

        user_id = activity.actor.id
        username = utils.get_user_name_for(user_id)
        message = activity.object.content
        room_id = activity.actor.url
        room_name = utils.get_room_name(room_id)
        channel_id = utils.get_channel_for_room(room_id)
        admin_room_id = utils.get_admin_room_for_channel(channel_id)

        activity_json = utils.activity_for_request_admin(user_id, username, room_id, room_name, message)
        environ.env.emit('gn_request_admin', activity_json, json=True, broadcast=True, room=admin_room_id)


@environ.env.observer.on('on_request_admin')
def _on_request_admin_send_request(arg: tuple) -> None:
    OnRequestAdminHooks.send_request(arg)
