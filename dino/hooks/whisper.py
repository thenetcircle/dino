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


class OnWhisperHooks(object):
    @staticmethod
    def send_whisper(arg: tuple) -> None:
        data, activity = arg
        user_room = activity.target.id
        whisperer = activity.actor.id
        room_id = activity.actor.url
        channel_id = activity.object.url

        whisperer_name = utils.get_user_name_for(whisperer)
        channel_name = utils.get_channel_name(channel_id)
        room_name = utils.get_room_name(room_id)

        activity_json = utils.activity_for_whisper(whisperer, whisperer_name, room_id, room_name, channel_id, channel_name)
        environ.env.emit('gn_whisper', activity_json, json=True, room=user_room)


@environ.env.observer.on('on_whisper')
def _on_whisper_send_whisper(arg: tuple) -> None:
    OnWhisperHooks.send_whisper(arg)
