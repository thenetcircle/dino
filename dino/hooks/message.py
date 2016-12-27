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


class OnMessageHooks(object):
    @staticmethod
    def store(arg: tuple) -> None:
        data, activity = arg
        environ.env.storage.store_message(activity)

    @staticmethod
    def update_last_read(arg: tuple) -> None:
        data, activity = arg
        room_id = activity.target.id
        if activity.target.object_type == 'private':
            utils.update_last_reads_private(room_id)
        else:
            utils.update_last_reads(room_id)

    @staticmethod
    def broadcast(arg: tuple) -> None:
        data, activity = arg
        room_id = activity.target.id
        environ.env.send(data, json=True, room=room_id, broadcast=True)


@environ.env.observer.on('on_message')
def _on_message_store(arg: tuple) -> None:
    OnMessageHooks.store(arg)


@environ.env.observer.on('on_message')
def _on_message_update_last_read(arg: tuple) -> None:
    OnMessageHooks.update_last_read(arg)


@environ.env.observer.on('on_message')
def _on_message_broadcast(arg: tuple) -> None:
    OnMessageHooks.broadcast(arg)
