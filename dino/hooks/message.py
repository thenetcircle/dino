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


class OnMessageHooks(object):
    @staticmethod
    def store(arg: tuple) -> None:
        data, activity = arg
        try:
            environ.env.storage.store_message(activity)
        except Exception as e:
            logger.error('could not store message %s because: %s' % (activity.id, str(e)))
            logger.error(str(data))
            logger.exception(traceback.format_exc())

    @staticmethod
    def update_last_read(arg: tuple) -> None:
        data, activity = arg
        room_id = activity.target.id
        if activity.target.object_type == 'private':
            utils.update_last_reads_private(room_id)
        else:
            utils.update_last_reads(room_id)

    @staticmethod
    def publish_activity(arg: tuple) -> None:
        data, activity = arg
        user_id = activity.actor.id
        user_name = activity.actor.display_name
        if utils.is_base64(user_name):
            user_name = utils.b64d(user_name)

        activity_json = utils.activity_for_message(user_id, user_name)
        environ.env.publish(activity_json)

    @staticmethod
    def broadcast(arg: tuple) -> None:
        data, activity = arg
        if utils.used_blacklisted_word(activity):
            return
        room_id = activity.target.id
        user_id = activity.actor.id
        if utils.user_is_invisible(user_id):
            data['actor']['attachments'] = utils.get_user_info_attachments_for(user_id)
        environ.env.send(data, json=True, room=room_id, broadcast=True)


@environ.env.observer.on('on_message')
def _on_message_publish_activity(arg: tuple) -> None:
    OnMessageHooks.publish_activity(arg)


@environ.env.observer.on('on_message')
def _on_message_store(arg: tuple) -> None:
    OnMessageHooks.store(arg)


@environ.env.observer.on('on_message')
def _on_message_update_last_read(arg: tuple) -> None:
    OnMessageHooks.update_last_read(arg)


@environ.env.observer.on('on_message')
def _on_message_broadcast(arg: tuple) -> None:
    OnMessageHooks.broadcast(arg)
