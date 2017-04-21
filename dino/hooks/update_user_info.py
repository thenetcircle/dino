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

import logging
import traceback

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


class OnUpdateUserInfoHooks(object):
    @staticmethod
    def broadcast(arg: tuple) -> None:
        orig_data, activity = arg
        data = {
            'actor': {
                'id': activity.actor.id,
                'displayName': activity.actor.display_name
            },
            'verb': 'update',
            'object': {
                'objectType': 'userInfo',
                'attachments': list()
            },
            'id': activity.id,
            'published': activity.published
        }

        if not hasattr(activity.object, 'attachments') or len(activity.object.attachments) == 0:
            logger.warn('empty object.attachments: %s' % str(orig_data))
            return

        for attachment in activity.object.attachments:
            data['object']['attachments'].append({
                'content': attachment.content,
                'objectType': attachment.object_type,
            })

        logger.info('about to send updated user info: %s' % str(data))
        room_uuid = None
        if hasattr(activity, 'target') and hasattr(activity.target, 'id'):
            target_id = activity.target.id
            if target_id is not None and len(target_id.strip()) > 0:
                room_uuid = target_id

        if room_uuid is not None:
            environ.env.emit('gn_user_info_updated', data, json=True, broadcast=True, room=room_uuid)
        else:
            rooms = utils.rooms_for_user(activity.actor.id)
            for room_uuid in rooms:
                data_copy = data.copy()
                data_copy['target'] = {'id': room_uuid}
                environ.env.emit('gn_user_info_updated', data, json=True, broadcast=True, room=room_uuid)


@environ.env.observer.on('on_update_user_info')
def _on_update_user_info_do_broadcast(arg: tuple) -> None:
    OnUpdateUserInfoHooks.broadcast(arg)
