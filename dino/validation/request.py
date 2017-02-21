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
from activitystreams.models.defobject import DefObject
from activitystreams.models.actor import Actor
from activitystreams.models.target import Target
import logging

from dino import environ
from dino import utils
from dino.config import SessionKeys
from dino.config import ApiActions
from dino.config import ApiTargets
from dino.config import ConfigKeys
from dino.config import ErrorCodes as ECodes
from dino.validation.base import BaseValidator
from dino.exceptions import NoSuchRoomException
from dino.exceptions import NoSuchUserException
from dino.exceptions import NoSuchChannelException
from dino.exceptions import NoChannelFoundException
from dino import validation
from dino.validation.duration import DurationValidator

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


class RequestValidator(BaseValidator):
    def on_message(self, activity: Activity) -> (bool, int, str):
        room_id = activity.target.id
        user_id = activity.actor.id
        object_type = activity.target.object_type
        message = activity.object.content

        from_room_id = None
        if hasattr(activity.actor, 'url'):
            from_room_id = activity.actor.url

        if message is None or len(message.strip()) == 0:
            return False, ECodes.EMPTY_MESSAGE, 'empty message body'

        if not utils.is_base64(message):
            return False, ECodes.NOT_BASE64, 'invalid message content, not base64 encoded'

        if room_id is None or room_id == '':
            return False, ECodes.MISSING_TARGET_ID, 'no room id specified when sending message'

        if object_type not in ['room', 'private']:
            return False, ECodes.INVALID_TARGET_TYPE, 'invalid object_type "%s", must be one of [room, private]' % object_type

        if object_type == 'room':
            channel_id = None
            if hasattr(activity, 'object') and hasattr(activity.object, 'url'):
                channel_id = activity.object.url
            if channel_id is None or len(channel_id.strip()) == 0:
                channel_id = utils.get_channel_for_room(room_id)

            if channel_id is None or channel_id == '':
                return False, ECodes.MISSING_OBJECT_URL, 'no channel id specified when sending message'

            activity.object.url = channel_id
            activity.object.display_name = utils.get_channel_name(channel_id)

            if not utils.channel_exists(channel_id):
                return False, ECodes.NO_SUCH_CHANNEL, 'channel %s does not exists' % channel_id

            if not utils.room_exists(channel_id, room_id):
                return False, ECodes.NO_SUCH_ROOM, 'target room %s does not exist' % room_id

            if from_room_id is not None:
                if from_room_id != room_id and not utils.room_exists(channel_id, from_room_id):
                    return False, ECodes.NO_SUCH_ROOM, 'origin room %s does not exist' % from_room_id

            if not utils.is_user_in_room(user_id, room_id):
                if from_room_id is None:
                    return False, ECodes.USER_NOT_IN_ROOM, 'user is not in target room'
                if not utils.is_user_in_room(user_id, from_room_id):
                    return False, ECodes.USER_NOT_IN_ROOM, 'user is not in origin room, cannot send message from there'
                if not utils.can_send_cross_room(activity, from_room_id, room_id):
                    return False, ECodes.NOT_ALLOWED, 'user not allowed to send cross-room msg from %s to %s' % (from_room_id, room_id)

        elif object_type == 'private':
            try:
                utils.get_user_name_for(room_id)
            except NoSuchUserException:
                return False, ECodes.INVALID_TARGET_TYPE, 'target.id is not a known user id'

        return True, None, None

    def on_delete(self, activity: Activity) -> (bool, int, str):
        user_id = activity.actor.id
        room_id = activity.target.id

        if not utils.user_is_allowed_to_delete_message(room_id, user_id):
            return False, ECodes.NOT_ALLOWED, 'not allowed to remove message in room %s' % room_id
        return True, None, None

    def on_login(self, activity: Activity) -> (bool, int, str):
        user_id = activity.actor.id

        is_banned, duration = utils.is_banned_globally(user_id)
        if is_banned:
            environ.env.disconnect()
            return False, ECodes.USER_IS_BANNED, 'user is banned from chatting for: %ss' % duration

        if hasattr(activity.actor, 'attachments') and activity.actor.attachments is not None:
            for attachment in activity.actor.attachments:
                environ.env.session[attachment.object_type] = attachment.content

        if SessionKeys.token.value not in environ.env.session:
            environ.env.disconnect()
            return False, ECodes.NO_USER_IN_SESSION, 'no token in session'

        token = environ.env.session.get(SessionKeys.token.value)
        is_valid, error_msg, session = self.validate_login(user_id, token)

        if not is_valid:
            environ.env.stats.incr('on_login.failed')
            environ.env.disconnect()
            return False, ECodes.NOT_ALLOWED, error_msg

        for session_key, session_value in session.items():
            environ.env.session[session_key] = session_value

        return True, None, None

    def on_disconnect(self, activity: Activity) -> (bool, int, str):
        user_id = environ.env.session.get(SessionKeys.user_id.value)
        user_name = environ.env.session.get(SessionKeys.user_name.value)
        if user_id is None or not isinstance(user_id, str) or user_name is None:
            return False, ECodes.NO_USER_IN_SESSION, 'no user in session, not connected'
        return True, None, None

    def on_ban(self, activity: Activity) -> (bool, int, str):
        room_id = activity.target.id
        user_id = activity.actor.id
        kicked_id = activity.object.id
        ban_duration = activity.object.summary

        channel_id = None
        if hasattr(activity, 'object') and hasattr(activity.object, 'url'):
            channel_id = activity.object.url
        if channel_id is None or len(channel_id.strip()) == 0:
            channel_id = utils.get_channel_for_room(room_id)

        try:
            DurationValidator(ban_duration)
        except ValueError as e:
            return False, ECodes.INVALID_BAN_DURATION, 'invalid ban duration: %s' % str(e)

        if room_id is not None and len(room_id.strip()) > 0:
            try:
                utils.get_room_name(room_id)
            except NoSuchRoomException as e:
                return False, ECodes.NO_SUCH_ROOM, 'no room found for uuid: %s' % str(e)

        is_global_ban = room_id is None or room_id == ''

        if kicked_id is None or kicked_id.strip() == '':
            return False, ECodes.MISSING_OBJECT_ID, 'got blank user id, can not ban'

        if not is_global_ban and not utils.room_exists(channel_id, room_id):
            return False, ECodes.NO_SUCH_ROOM, 'no room with id "%s" exists' % room_id

        if not is_global_ban:
            if not utils.is_owner(room_id, user_id):
                return False, ECodes.NOT_ALLOWED, 'only owners can ban'
        elif not utils.is_admin(channel_id, user_id) and not utils.is_super_user(user_id):
            return False, ECodes.NOT_ALLOWED, 'only admins and super users can do global bans'

        return True, None, None

    def on_request_admin(self, activity: Activity) -> (bool, int, str):
        activity.actor = Actor({
            'id': str(environ.env.session.get(SessionKeys.user_id.value)),
            'displayName': environ.env.session.get(SessionKeys.user_name.value)
        })

        room_id = activity.target.id
        channel_id = utils.get_channel_for_room(room_id)
        admin_room_id = utils.get_admin_room()

        if admin_room_id is None or len(admin_room_id.strip()) == 0:
            logger.error('no admin room found for channel "%s"' % channel_id)
            return False, ECodes.NO_ADMIN_ROOM_FOUND, 'no admin room for this channel'
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
                channel_id = None
                if hasattr(activity, 'object') and hasattr(activity.object, 'url'):
                    channel_id = activity.object.url
                if channel_id is None or len(channel_id.strip()) == 0:
                    channel_id = utils.get_channel_for_room(_target_id)
                if channel_id is not None and utils.is_owner_channel(channel_id, _user_id):
                    return True

            if utils.is_super_user(_user_id):
                return True
            return False

        user_id = activity.actor.id
        target_id = activity.target.id
        object_type = activity.target.object_type

        if object_type is None or len(object_type.strip()) == 0:
            return False, ECodes.INVALID_TARGET_TYPE, 'empty object_type, must be one of [channel, room]'

        if object_type not in ['channel', 'room']:
            return False, ECodes.INVALID_TARGET_TYPE, 'invalid object_type "%s", must be one of [channel, room]' % object_type

        if not _can_edit_acl(target_id, user_id):
            return False, ECodes.NOT_ALLOWED, 'user is not allowed to change acls on the target'

        # validate all acls before actually changing anything
        acls = activity.object.attachments
        all_available_acls_types = environ.env.config.get(ConfigKeys.ACL)['available']['acls']
        for acl in acls:
            if acl.object_type not in all_available_acls_types:
                return False, ECodes.INVALID_ACL_TYPE, 'invalid acl type "%s"' % acl.object_type

            if acl.summary is None or acl.summary not in ApiActions.all_api_actions:
                return False, ECodes.INVALID_ACL_ACTION, 'invalid api action "%s"' % acl.summary

            if not validation.acl.is_acl_valid(acl.object_type, acl.content):
                return False, ECodes.INVALID_ACL_VALUE, 'invalid acl value "%s" for type "%s"' % (acl.content, acl.object_type)

        return True, None, None

    def on_join(self, activity: Activity) -> (bool, int, str):
        room_id = activity.target.id
        user_id = activity.actor.id

        try:
            utils.get_room_name(room_id)
        except NoSuchRoomException:
            return False, ECodes.NO_SUCH_ROOM, 'room does not exist'

        if not hasattr(activity, 'object'):
            activity.object = DefObject(dict())

        channel_id = utils.get_channel_for_room(room_id)
        activity.object.url = channel_id
        activity.object.display_name = utils.get_channel_name(channel_id)

        activity.target.object_type = 'room'
        acls = utils.get_acls_in_room_for_action(room_id, ApiActions.JOIN)
        is_valid, error_msg = validation.acl.validate_acl_for_action(activity, ApiTargets.ROOM, ApiActions.JOIN, acls)
        if not is_valid:
            return False, ECodes.NOT_ALLOWED, error_msg

        is_banned, msg = utils.is_banned(user_id, room_id)
        if is_banned:
            return False, ECodes.USER_IS_BANNED, msg

        return True, None, None

    def on_leave(self, activity: Activity) -> (bool, int, str):
        if not hasattr(activity, 'target') or not hasattr(activity.target, 'id'):
            return False, ECodes.MISSING_TARGET_ID, 'room_id is None when trying to leave room'
        return True, None, None

    def on_list_channels(self, activity: Activity) -> (bool, int, str):
        return True, None, None

    def on_list_rooms(self, activity: Activity) -> (bool, int, str):
        if not hasattr(activity, 'object') or not hasattr(activity.object, 'url'):
            return False, ECodes.MISSING_OBJECT_URL, 'need channel ID to list rooms'

        channel_id = activity.object.url
        if channel_id is None or channel_id == '':
            return False, ECodes.MISSING_OBJECT_URL, 'need channel ID to list rooms'

        activity.target = Target({'objectType': 'channel'})
        acls = utils.get_acls_in_channel_for_action(channel_id, ApiActions.LIST)
        is_valid, msg = validation.acl.validate_acl_for_action(activity, ApiTargets.CHANNEL, ApiActions.LIST, acls)
        if not is_valid:
            return False, ECodes.NOT_ALLOWED, msg

        return True, None, None

    def on_users_in_room(self, activity: Activity) -> (bool, int, str):
        room_id = activity.target.id
        if room_id is None or len(room_id.strip()) == 0:
            return False, ECodes.MISSING_TARGET_ID, 'no room id specified'
        return True, None, None

    def on_history(self, activity: Activity) -> (bool, int, str):
        room_id = activity.target.id

        if room_id is None or room_id.strip() == '':
            return False, ECodes.MISSING_TARGET_ID, 'invalid target id'

        acls = utils.get_acls_in_room_for_action(room_id, ApiActions.HISTORY)
        is_valid, error_msg = validation.acl.validate_acl_for_action(
                activity, ApiTargets.ROOM, ApiActions.HISTORY, acls)

        if not is_valid:
            return False, ECodes.NOT_ALLOWED, error_msg

        return True, None, None

    def on_status(self, activity: Activity) -> (bool, int, str):
        user_name = environ.env.session.get(SessionKeys.user_name.value, None)
        status = activity.verb

        if user_name is None:
            return False, ECodes.NO_USER_IN_SESSION, 'no user name in session'

        is_valid, error_msg = validation.request.validate_request(activity)
        if not is_valid:
            return False, ECodes.NOT_ALLOWED, error_msg

        if status not in ['online', 'offline', 'invisible']:
            return False, ECodes.INVALID_STATUS, 'invalid status %s' % str(status)

        return True, None, None

    def on_get_acl(self, activity: Activity) -> (bool, int, str):
        if activity.target is None or not hasattr(activity.target, 'id'):
            return False, ECodes.MISSING_TARGET_ID, 'no target on activity'
        if activity.target.id is None or len(activity.target.id.strip()) == 0:
            return False, ECodes.MISSING_TARGET_ID, 'blank target id on activity'

        object_type = activity.target.object_type

        if object_type is None or len(object_type.strip()) == 0:
            return False, ECodes.INVALID_OBJECT_TYPE, 'blank object type on activity'
        if object_type not in ['room', 'channel']:
            return False, ECodes.INVALID_OBJECT_TYPE, 'unknown object type "%s", must be one of [channel, room]' % object_type

        return True, None, None

    def on_kick(self, activity: Activity) -> (bool, int, str):
        room_id = activity.target.id
        user_id = activity.object.id

        if room_id is None or room_id.strip() == '':
            return False, ECodes.MISSING_TARGET_ID, 'got blank room id, can not kick'

        try:
            utils.get_room_name(room_id)
        except NoSuchRoomException:
            return False, ECodes.NO_SUCH_ROOM, 'no room with id "%s" exists' % room_id

        if user_id is None or user_id.strip() == '':
            return False, ECodes.MISSING_TARGET_DISPLAY_NAME, 'got blank user id, can not kick'

        channel_id = utils.get_channel_for_room(room_id)
        channel_acls = utils.get_acls_in_channel_for_action(channel_id, ApiActions.KICK)
        is_valid, msg = validation.acl.validate_acl_for_action(activity, ApiTargets.CHANNEL, ApiActions.KICK, channel_acls)
        if not is_valid:
            return False, ECodes.NOT_ALLOWED, msg

        room_acls = utils.get_acls_in_room_for_action(room_id, ApiActions.KICK)
        is_valid, msg = validation.acl.validate_acl_for_action(activity, ApiTargets.ROOM, ApiActions.KICK, room_acls)
        if not is_valid:
            return False, ECodes.NOT_ALLOWED, msg

        return True, None, None

    def on_invite(self, activity: Activity) -> (bool, int, str):
        if not hasattr(activity.actor, 'url'):
            return False, ECodes.MISSING_ACTOR_URL, 'need invite room uuid in actor.url'
        invite_room = activity.actor.url

        if not hasattr(activity, 'target') or not hasattr(activity.target, 'id'):
            return False, ECodes.MISSING_TARGET_ID, 'no target.id (uuid of user to invite)'

        try:
            activity.target.display_name = utils.get_user_name_for(activity.target.id)
        except NoSuchUserException:
            return False, ECodes.NO_SUCH_USER, 'no such user for target.id (uuid of user to invite)'

        try:
            channel_id = utils.get_channel_for_room(invite_room)
        except (NoSuchRoomException, NoChannelFoundException):
            return False, ECodes.NO_SUCH_ROOM, 'no room/channel found for actor.url room uuid'

        if not utils.room_exists(channel_id, invite_room):
            return False, ECodes.NO_SUCH_ROOM, 'room actor.url does not exist'

        if not hasattr(activity, 'object'):
            activity.object = DefObject(dict())

        activity.object.url = channel_id
        activity.object.display_name = utils.get_channel_name(channel_id)

        return True, None, None

    def on_whisper(self, activity: Activity) -> (bool, int, str):
        if not hasattr(activity, 'target') or not hasattr(activity.target, 'id'):
            return False, ECodes.MISSING_TARGET_ID, 'no target.id (user uuid to whisper to)'
        if not hasattr(activity, 'actor') or not hasattr(activity.actor, 'id'):
            return False, ECodes.MISSING_ACTOR_ID, 'no actor.id (id of user who is whispering)'
        if not hasattr(activity, 'actor') or not hasattr(activity.actor, 'url'):
            return False, ECodes.MISSING_ACTOR_URL, 'no actor.url (room uuid to whisper in)'
        if not hasattr(activity, 'object') or not hasattr(activity.object, 'content'):
            return False, ECodes.MISSING_OBJECT_CONTENT, 'no object.content (message to whisper)'

        if not utils.is_base64(activity.object.content):
            return False, ECodes.NOT_BASE64, 'object.content needs to be base64 encoded'

        try:
            activity.object.url = utils.get_channel_for_room(activity.actor.url)
        except (NoSuchChannelException, NoChannelFoundException):
            return False, ECodes.NO_SUCH_ROOM, 'no room found for actor.url (room uuid to whisper in)'

        try:
            activity.object.display_name = utils.get_channel_name(activity.object.url)
        except (NoSuchChannelException, NoChannelFoundException):
            return False, ECodes.NO_SUCH_CHANNEL, 'no channel found for actor.url (room uuid to whisper in)'

        return True, None, None

    def on_create(self, activity: Activity) -> (bool, int, str):
        if not hasattr(activity, 'object') or not hasattr(activity.object, 'url'):
            return False, ECodes.MISSING_OBJECT_URL, 'no channel id set'
        if not hasattr(activity.target, 'display_name'):
            return False, ECodes.MISSING_TARGET_DISPLAY_NAME, 'no room name set'

        room_name = activity.target.display_name
        channel_id = activity.object.url

        if not hasattr(activity, 'actor') or not hasattr(activity.actor, 'id'):
            return False, ECodes.MISSING_ACTOR_ID, 'need actor.id (user uuid)'

        try:
            activity.object.display_name = utils.get_channel_name(channel_id)
        except NoSuchChannelException:
            return False, ECodes.NO_SUCH_CHANNEL, 'channel does not exist'

        if room_name is None or room_name.strip() == '':
            return False, ECodes.MISSING_TARGET_DISPLAY_NAME, 'got blank room name, can not create'

        if not utils.is_base64(room_name):
            return False, ECodes.NOT_BASE64, 'invalid room name, not base64 encoded'
        room_name = utils.b64d(room_name)

        if not environ.env.db.channel_exists(channel_id):
            return False, ECodes.NO_SUCH_CHANNEL, 'channel does not exist'

        if utils.room_name_restricted(room_name):
            return False, ECodes.NOT_ALLOWED, 'restricted room name'

        if environ.env.db.room_name_exists(channel_id, room_name):
            return False, ECodes.ROOM_ALREADY_EXISTS, 'a room with that name already exists'

        return True, None, None

    def on_test(self, activity: Activity):
        """ only used for testing decorators """
        return True, None, None
