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

from activitystreams import Activity

from dino import environ
from dino import utils

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class OnCreateHooks(object):
    @staticmethod
    def _get_owners(activity: Activity) -> list:
        if not hasattr(activity.target, 'attachments') or activity.target.attachments is None:
            return list()
        for attachment in activity.target.attachments:
            if not hasattr(attachment, 'object_type'):
                continue
            if attachment.object_type == 'owners' and hasattr(attachment, 'summary'):
                all_owners = set(attachment.summary.split(','))
                return [owner.strip() for owner in all_owners if len(owner.strip()) > 0]
        return list()

    @staticmethod
    def create_room(arg: tuple) -> None:
        data, activity = arg
        room_name = activity.target.display_name
        room_id = activity.target.id
        channel_id = activity.object.url
        user_id = activity.actor.id
        user_name = activity.actor.display_name

        object_type = 'unknown'
        if hasattr(activity.target, 'object_type'):
            object_type = activity.target.object_type

        is_ephemeral = object_type != 'private'
        owners = OnCreateHooks._get_owners(activity)

        if utils.is_base64(room_name):
            room_name = utils.b64d(room_name)
        environ.env.db.create_room(room_name, room_id, channel_id, user_id, user_name, ephemeral=is_ephemeral)

        for owner_id in owners:
            environ.env.db.set_owner(room_id, owner_id)

    @staticmethod
    def emit_creation_event(arg: tuple) -> None:
        data, activity = arg
        activity_json = utils.activity_for_create_room(data, activity)

        # only send creation even to everyone if it's a public room
        if activity.target.object_type == 'private':
            owners = OnCreateHooks._get_owners(activity)
            for owner_id in owners:
                environ.env.emit('gn_room_created', activity_json, room=owner_id)
        else:
            environ.env.emit(
                'gn_room_created', activity_json, broadcast=True, json=True,
                include_self=True, namespace='/ws')


@environ.env.observer.on('on_create')
def _on_create_create_room(arg: tuple) -> None:
    OnCreateHooks.create_room(arg)


@environ.env.observer.on('on_create')
def _on_create_emit_creation_event(arg: tuple) -> None:
    OnCreateHooks.emit_creation_event(arg)
