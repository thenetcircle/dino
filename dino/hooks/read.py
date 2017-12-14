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

import eventlet
from activitystreams import Activity

from dino import environ

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class OnReadHooks(object):
    @staticmethod
    def update_messages(activity: Activity) -> None:
        message_ids = {attachment.id for attachment in activity.object.attachments}
        environ.env.storage.mark_as_read(message_ids, activity.actor.id, activity.target.id)


@environ.env.observer.on('on_read')
def _on_read_update_messages(arg: tuple) -> None:
    _, activity = arg
    eventlet.spawn(OnReadHooks.update_messages, activity)
