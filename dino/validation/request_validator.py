#!/usr/bin/env python

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

from activitystreams import parse as as_parser
from dino import utils
from dino.validation import BaseValidator

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class RequestValidator(BaseValidator):
    def on_message(self, data):
        activity = as_parser(data)
        is_valid, error_msg = self.validate_request(activity)
        if not is_valid:
            return 400, error_msg

        room_id = activity.target.id
        from_room_id = activity.actor.url

        if room_id is None or room_id == '':
            return False, 400, 'no room id specified when sending message'

        if activity.target.object_type == 'group':
            channel_id = activity.object.url

            if channel_id is None or channel_id == '':
                return False, 400, 'no channel id specified when sending message'

            if not utils.channel_exists(channel_id):
                return False, 400, 'channel %s does not exists' % channel_id

            if not utils.room_exists(channel_id, room_id):
                return False, 400, 'target room %s does not exist' % room_id

            if from_room_id is not None:
                if from_room_id != room_id and not utils.room_exists(channel_id, from_room_id):
                    return False, 400, 'origin room %s does not exist' % from_room_id

            if not utils.is_user_in_room(activity.actor.id, room_id):
                if not utils.can_send_cross_group(from_room_id, room_id):
                    return False, 400, 'user not allowed to send cross-group msg from %s to %s' % (from_room_id, room_id)

        return True, None, None
