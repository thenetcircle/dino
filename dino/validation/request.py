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

from activitystreams.models.activity import Activity
import traceback
import base64
import logging

from dino import utils
from dino import environ
from dino.config import SessionKeys
from dino.config import ApiActions
from dino.config import ApiTargets
from dino.config import ConfigKeys
from dino.validation.base import BaseValidator
from dino import validation

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


class RequestValidator(BaseValidator):
    def on_message(self, activity: Activity) -> (bool, int, str):
        room_id = activity.target.id
        from_room_id = activity.actor.url
        user_id = activity.actor.id
        object_type = activity.target.object_type
        message = activity.object.content

        if message is None or len(message.strip()) == 0:
            return False, 400, 'empty message body'

        if not self._is_base64(message):
            return False, 400, 'invalid message content, not base64 encoded'

        if room_id is None or room_id == '':
            return False, 400, 'no room id specified when sending message'

        if object_type not in ['room', 'private']:
            return False, 400, 'invalid object_type "%s", must be one of [room, private]' % object_type

        if object_type == 'room':
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

            if not utils.is_user_in_room(user_id, room_id):
                if from_room_id is None:
                    return False, 400, 'user is not in target room'
                if not utils.is_user_in_room(user_id, from_room_id):
                    return False, 400, 'user is not in origin room, cannot send message from there'
                if not utils.can_send_cross_room(activity, from_room_id, room_id):
                    return False, 400, 'user not allowed to send cross-group msg from %s to %s' % (from_room_id, room_id)

        elif object_type == 'private':
            try:
                if not utils.is_room_private(room_id):
                    return False, 400, 'target is not a private chat, use object_type "group" instead'
            except Exception:
                print(traceback.format_exc())
                return False, 400, 'could not check private room'

        return True, None, None

    def on_delete(self, activity: Activity) -> (bool, int, str):
        user_id = activity.actor.id
        room_id = activity.target.id

        if not utils.user_is_allowed_to_delete_message(room_id, user_id):
            return False, 400, 'not allowed to remove message in room %s' % room_id
        return True, None, None

    def on_login(self, activity: Activity) -> (bool, int, str):
        user_id = activity.actor.id

        is_banned, duration = utils.is_banned_globally(user_id)
        if is_banned:
            return False, 400, 'user is banned from chatting for: %ss' % duration

        if activity.actor.attachments is not None:
            for attachment in activity.actor.attachments:
                environ.env.session[attachment.object_type] = attachment.content

        if SessionKeys.token.value not in environ.env.session:
            return False, 400, 'no token in session'

        token = environ.env.session.get(SessionKeys.token.value)
        is_valid, error_msg, session = self.validate_login(user_id, token)

        if not is_valid:
            return False, 400, error_msg

        for session_key, session_value in session.items():
            environ.env.session[session_key] = session_value

        return True, None, None

    def on_ban(self, activity: Activity) -> (bool, int, str):
        room_id = activity.target.id
        channel_id = activity.object.url
        user_id = activity.actor.id
        kicked_id = activity.object.id

        is_global_ban = room_id is None or room_id == ''

        if kicked_id is None or kicked_id.strip() == '':
            return False, 400, 'got blank user id, can not ban'

        if not utils.room_exists(channel_id, room_id):
            return False, 400, 'no room with id "%s" exists' % room_id

        if not is_global_ban:
            if not utils.is_owner(room_id, user_id):
                return False, 400, 'only owners can ban'
        elif not utils.is_admin(channel_id, user_id) and not utils.is_super_user(user_id):
            return False, 400, 'only admins and super users can do global bans'

        return True, None, None

    def on_set_acl(self, activity: Activity) -> (bool, int, str):
        def _can_edit_acl(_target_id: str, _user_id: str) -> bool:
            object_type = activity.target.object_type
            is_for_channel = object_type == 'channel'

            if is_for_channel:
                if utils.is_owner_channel(_target_id, _user_id):
                    return True
                if utils.is_admin(_target_id, _user_id):
                    return True
            else:
                if utils.is_owner(_target_id, _user_id):
                    return True
                if activity.object is not None:
                    channel_id = activity.object.url
                    if channel_id is not None and utils.is_owner_channel(channel_id, _user_id):
                        return True

            if utils.is_super_user(_user_id):
                return True
            return False

        user_id = activity.actor.id
        target_id = activity.target.id
        object_type = activity.target.object_type

        if object_type is None or len(object_type.strip()) == 0:
            return False, 400, 'empty object_type, must be one of [channel, room]'

        if object_type not in ['channel', 'room']:
            return False, 400, 'invalid object_type "%s", must be one of [channel, room]' % object_type

        if not _can_edit_acl(target_id, user_id):
            return False, 400, 'user is not allowed to change acls on the target'

        # validate all acls before actually changing anything
        acls = activity.object.attachments
        all_available_acls_types = environ.env.config.get(ConfigKeys.ACL)['available']['acls']
        for acl in acls:
            if acl.object_type not in all_available_acls_types:
                return False, 400, 'invalid acl type "%s"' % acl.object_type

            if acl.summary is None or acl.summary not in ApiActions.all_api_actions:
                return False, 400, 'invalid api action "%s"' % acl.summary

            if not validation.acl.is_acl_valid(acl.object_type, acl.content):
                return False, 400, 'invalid acl value "%s" for type "%s"' % (acl.content, acl.object_type)

        return True, None, None

    def on_join(self, activity: Activity) -> (bool, int, str):
        room_id = activity.target.id
        user_id = activity.actor.id

        acls = utils.get_acls_in_room_for_action(room_id, ApiActions.JOIN)
        is_valid, error_msg = validation.acl.validate_acl_for_action(activity, ApiTargets.ROOM, ApiActions.JOIN, acls)
        if not is_valid:
            return False, 400, error_msg

        is_banned, msg = utils.is_banned(user_id, room_id)
        if is_banned:
            return False, 400, msg

        return True, None, None

    def on_leave(self, activity: Activity) -> (bool, int, str):
        if not hasattr(activity, 'target') or not hasattr(activity.target, 'id'):
            return False, 400, 'room_id is None when trying to leave room'
        return True, None, None

    def on_list_channels(self, activity: Activity) -> (bool, int, str):
        return True, None, None

    def on_list_rooms(self, activity: Activity) -> (bool, int, str):
        channel_id = activity.object.url

        if channel_id is None or channel_id == '':
            return False, 400, 'need channel ID to list rooms'

        acls = utils.get_acls_in_channel_for_action(channel_id, ApiActions.LIST)
        is_valid, msg = validation.acl.validate_acl_for_action(activity, ApiTargets.CHANNEL, ApiActions.LIST, acls)
        if not is_valid:
            return False, 400, msg

        return True, None, None

    def on_users_in_room(self, activity: Activity) -> (bool, int, str):
        return True, None, None

    def on_history(self, activity: Activity) -> (bool, int, str):
        room_id = activity.target.id

        if room_id is None or room_id.strip() == '':
            return False, 400, 'invalid target id'

        acls = utils.get_acls_in_room_for_action(room_id, ApiActions.HISTORY)
        is_valid, error_msg = validation.acl.validate_acl_for_action(
                activity, ApiTargets.ROOM, ApiActions.HISTORY, acls)

        if not is_valid:
            return False, 400, error_msg

        return True, None, None

    def on_status(self, activity: Activity) -> (bool, int, str):
        user_name = environ.env.session.get(SessionKeys.user_name.value, None)
        status = activity.verb

        if user_name is None:
            return False, 400, 'no user name in session'

        is_valid, error_msg = validation.request.validate_request(activity)
        if not is_valid:
            return False, 400, error_msg

        if status not in ['online', 'offline', 'invisible']:
            return False, 400, 'invalid status %s' % str(status)

        return True, None, None

    def on_get_acl(self, activity: Activity) -> (bool, int, str):
        if activity.target is None:
            return False, 400, 'no target on activity'
        if activity.target.id is None or len(activity.target.id.strip()) == 0:
            return False, 400, 'blank target id on activity'

        object_type = activity.target.object_type

        if object_type is None or len(object_type.strip()) == 0:
            return False, 400, 'blank object type on activity'
        if object_type not in ['room', 'channel']:
            return False, 400, 'unknown object type "%s", must be one of [channel, room]' % object_type

        return True, None, None

    def on_kick(self, activity: Activity) -> (bool, int, str):
        room_id = activity.target.id
        channel_id = activity.object.url
        user_id = activity.target.display_name

        if channel_id is None or channel_id.strip() == '':
            return False, 400, 'got blank channel id, can not kick'

        if room_id is None or room_id.strip() == '':
            return False, 400, 'got blank room id, can not kick'

        if user_id is None or user_id.strip() == '':
            return False, 400, 'got blank user id, can not kick'

        if not environ.env.db.room_exists(channel_id, room_id):
            return False, 400, 'no room with id "%s" exists' % room_id

        channel_acls = utils.get_acls_in_room_for_action(channel_id, ApiActions.KICK)
        is_valid, msg = validation.acl.validate_acl_for_action(activity, ApiTargets.CHANNEL, ApiActions.KICK, channel_acls)
        if not is_valid:
            return False, 400, msg

        room_acls = utils.get_acls_in_room_for_action(room_id, ApiActions.KICK)
        is_valid, msg = validation.acl.validate_acl_for_action(activity, ApiTargets.ROOM, ApiActions.KICK, room_acls)
        if not is_valid:
            return False, 400, msg

        return True, None, None

    def on_invite(self, activity: Activity) -> (bool, int, str):
        # TODO: implement
        pass

    def on_create(self, activity: Activity) -> (bool, int, str):
        room_name = activity.target.display_name
        channel_id = activity.object.url

        if room_name is None or room_name.strip() == '':
            return False, 400, 'got blank room name, can not create'

        if not self._is_base64(room_name):
            return False, 400, 'invalid room name, not base64 encoded'

        if not environ.env.db.channel_exists(channel_id):
            return False, 400, 'channel does not exist'

        if environ.env.db.room_name_exists(channel_id, room_name):
            return False, 400, 'a room with that name already exists'

        return True, None, None

    def _is_base64(self, s):
        try:
            str(base64.b64decode(bytes(s, 'utf-8')), 'utf-8')
        except Exception as e:
            logger.warning('invalid message content, could not decode base64: %s' % str(e))
            print(traceback.format_exc())
            return False
        return True
