import logging

from activitystreams.models.activity import Activity

from dino.config import ConfigKeys
from dino.config import ErrorCodes as ECodes
from dino.config import SessionKeys
from dino.validation import RequestValidator
from dino.wio import environ
from dino.wio import utils
from dino.wio import validation
from dino.wio.utils.decorators import overrides

logger = logging.getLogger(__name__)


class RequestValidatorWio(RequestValidator):
    @overrides(RequestValidator)
    def on_login(self, activity: Activity) -> (bool, int, str):
        user_id = activity.actor.id

        is_banned, duration = utils.is_banned_globally(user_id)
        if is_banned:
            environ.env.join_room(user_id)
            reason = environ.env.db.get_reason_for_ban_global(user_id)
            json_act = utils.activity_for_already_banned(duration, reason)
            environ.env.emit(
                'gn_banned', json_act, json=True, room=user_id, broadcast=False, include_self=True, namespace='/ws')

            logger.info('user %s is banned from chatting for: %ss' % (user_id, duration))
            return False, ECodes.USER_IS_BANNED, 'user %s is banned from chatting for: %ss' % (user_id, duration)

        if hasattr(activity.actor, 'attachments') and activity.actor.attachments is not None:
            for attachment in activity.actor.attachments:
                environ.env.session[attachment.object_type] = attachment.content

        if SessionKeys.token.value not in environ.env.session:
            logger.warning('no token in session when logging in for user id %s' % str(user_id))
            return False, ECodes.NO_USER_IN_SESSION, 'no token in session'

        token = environ.env.session.get(SessionKeys.token.value)
        is_valid, error_msg, session = self.validate_login(user_id, token)

        if not is_valid:
            logger.warning('login is not valid for user id %s: %s' % (str(user_id), str(error_msg)))
            environ.env.stats.incr('on_login.failed')
            return False, ECodes.NOT_ALLOWED, error_msg

        for session_key, session_value in session.items():
            environ.env.session[session_key] = session_value

        return True, None, None

    @overrides(RequestValidator)
    def on_update_user_info(self, activity: Activity) -> (bool, int, str):
        if not hasattr(activity, 'object'):
            return False, ECodes.MISSING_OBJECT, 'no object on activity'
        if not hasattr(activity.object, 'attachments'):
            return False, ECodes.MISSING_OBJECT_ATTACHMENTS, 'no attachments on object'
        if len(activity.object.attachments) == 0:
            return False, ECodes.MISSING_OBJECT_ATTACHMENTS, 'no attachments on object'

        attachments = activity.object.attachments
        for attachment in attachments:
            if not hasattr(attachment, 'object_type') or len(attachment.object_type.strip()) == 0:
                logger.warning('no object.attachments.objectType specified')
                return False, ECodes.MISSING_ATTACHMENT_TYPE, 'no objectType on attachment for object'
            if not hasattr(attachment, 'content') or len(attachment.content.strip()) == 0:
                logger.warning('no object.attachments.content specified')
                return False, ECodes.MISSING_ATTACHMENT_CONTENT, 'no content on attachment for object'
            if not utils.is_base64(attachment.content):
                return False, ECodes.NOT_BASE64, 'content on attachment for object is not base64 encoded'
        return True, None, None

    @overrides(RequestValidator)
    def _can_be_invisible(self, user_id: str):
        if environ.env.config.get(ConfigKeys.INVISIBLE_UNRESTRICTED, default=False):
            return True
        if utils.is_super_user(user_id) or utils.is_global_moderator(user_id):
            return True
        return False

    @overrides(RequestValidator)
    def on_status(self, activity: Activity) -> (bool, int, str):
        user_name = environ.env.session.get(SessionKeys.user_name.value, None)
        user_id = environ.env.session.get(SessionKeys.user_id.value, None)
        status = activity.verb

        if user_name is None:
            return False, ECodes.NO_USER_IN_SESSION, 'no user name in session'

        is_valid, error_msg = validation.request.validate_request(activity)
        if not is_valid:
            return False, ECodes.NOT_ALLOWED, error_msg

        if status not in ['online', 'offline', 'invisible']:
            return False, ECodes.INVALID_STATUS, 'invalid status %s' % str(status)

        if status == 'invisible' and not self._can_be_invisible(user_id):
            return False, ECodes.NOT_ALLOWED, 'only ops can be invisible'

        return True, None, None

    @overrides(RequestValidator)
    def on_msg_status(self, _: Activity) -> (bool, int, str):
        raise NotImplementedError()

    @overrides(RequestValidator)
    def on_message(self, activity: Activity) -> (bool, int, str):
        raise NotImplementedError()

    @overrides(RequestValidator)
    def _on_read_or_receive(self, activity: Activity, expected_verb: str) -> (bool, int, str):
        raise NotImplementedError()

    @overrides(RequestValidator)
    def on_read(self, activity: Activity) -> (bool, int, str):
        raise NotImplementedError()

    @overrides(RequestValidator)
    def on_received(self, activity: Activity) -> (bool, int, str):
        raise NotImplementedError()

    @overrides(RequestValidator)
    def on_delete(self, activity: Activity) -> (bool, int, str):
        raise NotImplementedError()

    @overrides(RequestValidator)
    def on_remove_room(self, activity: Activity) -> (bool, int, str):
        raise NotImplementedError()

    @overrides(RequestValidator)
    def on_report(self, activity: Activity) -> (bool, int, str):
        raise NotImplementedError()

    @overrides(RequestValidator)
    def on_ban(self, activity: Activity) -> (bool, int, str):
        raise NotImplementedError()

    @overrides(RequestValidator)
    def on_request_admin(self, activity: Activity) -> (bool, int, str):
        raise NotImplementedError()

    @overrides(RequestValidator)
    def on_set_acl(self, activity: Activity) -> (bool, int, str):
        raise NotImplementedError()

    @overrides(RequestValidator)
    def on_join(self, activity: Activity) -> (bool, int, str):
        raise NotImplementedError()

    @overrides(RequestValidator)
    def on_leave(self, activity: Activity) -> (bool, int, str):
        raise NotImplementedError()

    @overrides(RequestValidator)
    def on_list_channels(self, activity: Activity) -> (bool, int, str):
        raise NotImplementedError()

    @overrides(RequestValidator)
    def on_list_rooms(self, activity: Activity) -> (bool, int, str):
        raise NotImplementedError()

    @overrides(RequestValidator)
    def on_users_in_room(self, activity: Activity) -> (bool, int, str):
        raise NotImplementedError()

    @overrides(RequestValidator)
    def on_history(self, activity: Activity) -> (bool, int, str):
        raise NotImplementedError()

    @overrides(RequestValidator)
    def on_get_acl(self, activity: Activity) -> (bool, int, str):
        raise NotImplementedError()

    @overrides(RequestValidator)
    def on_kick(self, activity: Activity) -> (bool, int, str):
        raise NotImplementedError()

    @overrides(RequestValidator)
    def on_invite(self, activity: Activity) -> (bool, int, str):
        raise NotImplementedError()

    @overrides(RequestValidator)
    def on_whisper(self, activity: Activity) -> (bool, int, str):
        raise NotImplementedError()

    @overrides(RequestValidator)
    def on_create(self, activity: Activity) -> (bool, int, str):
        raise NotImplementedError()
