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
import sys
import traceback

from activitystreams import parse as as_parser

from dino import environ
from dino import utils
from dino.endpoint import sockets
from dino.config import ConfigKeys

from datetime import datetime
from uuid import uuid4 as uuid
import logging

logger = logging.getLogger(__name__)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class OnKickHooks(object):
    DEFAULT_BAN_DURATION = str(60 * 10) + "s"  # 10 minutes

    @staticmethod
    def create_ban_and_publish_kick_activity(arg: tuple) -> None:
        data, activity = arg

        banned_id = activity.object.id
        banner_id = activity.actor.id
        room_id = activity.target.id
        reason = None

        # reason is already base64 encoded on the request
        if activity.object.content is not None:
            reason = activity.object.content

        ban_datetime = utils.ban_duration_to_datetime(OnKickHooks.DEFAULT_BAN_DURATION)
        ban_timestamp_int = str(int(ban_datetime.timestamp()))
        ban_timestamp_str = ban_datetime.strftime(ConfigKeys.DEFAULT_DATE_FORMAT)

        # could be a global kick, not a single room kick
        if activity.target is not None:
            try:
                environ.env.db.ban_user_room(
                    user_id=banned_id,
                    ban_timestamp=ban_timestamp_int,
                    ban_duration=OnKickHooks.DEFAULT_BAN_DURATION,
                    room_id=room_id,
                    reason=reason,
                    banner_id=banner_id
                )
            except Exception as e:
                logger.error('failed to ban user %s from room %s: %s' % (banned_id, room_id, str(e)))
                environ.env.capture_exception(sys.exc_info())
                # keep going, we still want to publish the kick activity

        namespace = activity.target.url
        if namespace is None or len(namespace.strip()) == 0:
            namespace = environ.env.request.namespace

        kick_activity = {
            'actor': {
                'id': activity.actor.id,
                'displayName': activity.actor.display_name
            },
            'verb': 'kick',
            'object': {
                'id': activity.object.id,
                'summary': OnKickHooks.DEFAULT_BAN_DURATION,
                'updated': ban_timestamp_str
            },
            'target': {
                'url': namespace
            },
            'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT),
            'id': str(uuid())
        }

        if activity.object.display_name is not None:
            kick_activity['object']['displayName'] = activity.object.display_name

        if reason is not None:
            kick_activity['object']['content'] = reason

        # when banning globally, no target room is specified
        if activity.target is not None:
            kick_activity['target']['id'] = activity.target.id
            kick_activity['target']['displayName'] = activity.target.display_name

        sockets.queue_handler.handle_server_activity(kick_activity, as_parser(kick_activity))


@environ.env.observer.on('on_kick')
def _on_kick_publish_activity(arg: tuple) -> None:
    OnKickHooks.create_ban_and_publish_kick_activity(arg)
