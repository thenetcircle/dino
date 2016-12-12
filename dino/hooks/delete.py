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

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class OnDeleteHooks(object):
    @staticmethod
    def remove_from_storage(arg: tuple) -> None:
        data, activity = arg
        message_id = activity.object.id
        environ.env.storage.delete_message(message_id)

    @staticmethod
    def broadcast_deletion(arg: tuple) -> None:
        data, activity = arg
        room_id = activity.target.id
        environ.env.send(data, json=True, room=room_id, broadcast=True)


@environ.env.observer.on('on_delete')
def _on_delete_remove_from_storage(arg: tuple) -> None:
    OnDeleteHooks.remove_from_storage(arg)


@environ.env.observer.on('on_delete')
def _on_delete_broadcast_deletion(arg: tuple) -> None:
    OnDeleteHooks.broadcast_deletion(arg)
