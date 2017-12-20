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

import logging

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


class OnUpdateUserInfoHooks(object):
    @staticmethod
    def update_cache(arg: tuple) -> None:
        _, activity = arg
        environ.env.cache.reset_user_info(activity.actor.id)

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
            logger.warning('empty object.attachments: %s' % str(orig_data))
            return

        user_id = environ.env.session.get(SessionKeys.user_id.value, activity.actor.id)
        user_name = environ.env.session.get(SessionKeys.user_name.value, activity.actor.display_name)
        protected_keys = {
            SessionKeys.user_id.value,
            SessionKeys.token.value
        }

        for attachment in activity.object.attachments:
            if attachment.object_type in protected_keys:
                logger.warning('user "%s" (%s) tried to change protected key "%s", skipping' % attachment.object_type)

            decoded = utils.b64d(attachment.content)
            if attachment.object_type in SessionKeys._member_names_:
                environ.env.session[attachment.object_type] = decoded
            else:
                logger.warning(
                        'key "%s" is not a predefined, not updating session for "%s" (%s), value was "%s"' %
                        (attachment.object_type, user_name, user_id, decoded))

            environ.env.auth.update_session_for_key(user_id, attachment.object_type, decoded)
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
            environ.env.emit('gn_user_info_updated', data, json=True, broadcast=True, room=room_uuid, namespace='/ws')
        else:
            rooms = utils.rooms_for_user(activity.actor.id)
            for room_uuid in rooms:
                data_copy = data.copy()
                data_copy['target'] = {'id': room_uuid}
                environ.env.emit(
                    'gn_user_info_updated', data, json=True, broadcast=True, room=room_uuid, namespace='/ws')


@environ.env.observer.on('on_update_user_info')
def _on_update_user_info_do_broadcast(arg: tuple) -> None:
    OnUpdateUserInfoHooks.broadcast(arg)


@environ.env.observer.on('on_update_user_info')
def _on_update_user_info_update_cache(arg: tuple) -> None:
    OnUpdateUserInfoHooks.update_cache(arg)
