import logging
import sys
import traceback

import activitystreams

from dino.utils.activity_helper import ActivityBuilder

from dino import environ
from dino import utils
from dino import validation
from dino.config import SessionKeys, ConfigKeys, ApiActions, ApiTargets
from dino.config import UserKeys
from dino.exceptions import NoSuchUserException

logger = logging.getLogger(__name__)


class OnLoginHooks(object):
    @staticmethod
    def update_session_and_join_private_room(arg: tuple) -> None:
        data, activity = arg
        user_id = activity.actor.id
        user_name = utils.b64d(activity.actor.display_name)
        environ.env.session[SessionKeys.user_id.value] = user_id
        environ.env.session[SessionKeys.user_name.value] = user_name

        try:
            user_agent_string = environ.env.request.user_agent.string
            user_agent_platform = environ.env.request.user_agent.platform
            user_agent_browser = environ.env.request.user_agent.browser
            user_agent_version = environ.env.request.user_agent.version
            user_agent_language = environ.env.request.user_agent.language
        except Exception as e:
            logger.error('could not get user agent for user "{}": {}'.format(user_id, str(e)))
            logger.exception(traceback.format_exc())
            environ.env.capture_exception(sys.exc_info())
            user_agent_string = ''
            user_agent_platform = ''
            user_agent_browser = ''
            user_agent_version = ''
            user_agent_language = ''

        environ.env.session[SessionKeys.user_agent.value] = user_agent_string or ''
        environ.env.session[SessionKeys.user_agent_browser.value] = user_agent_browser or ''
        environ.env.session[SessionKeys.user_agent_version.value] = user_agent_version or ''
        environ.env.session[SessionKeys.user_agent_platform.value] = user_agent_platform or ''
        environ.env.session[SessionKeys.user_agent_language.value] = user_agent_language or ''

        avatar_url = environ.env.session.get(SessionKeys.avatar.value) or ''
        app_avatar_url = environ.env.session.get(SessionKeys.app_avatar.value) or ''
        app_avatar_safe = environ.env.session.get(SessionKeys.app_avatar_safe.value) or ''

        environ.env.db.set_avatar_for(user_id, avatar_url, app_avatar_url, app_avatar_safe)

        if activity.actor.image is None:
            environ.env.session['image_url'] = ''
            environ.env.session[SessionKeys.image.value] = 'n'
        else:
            environ.env.session['image_url'] = activity.actor.image.url
            environ.env.session[SessionKeys.image.value] = 'y'

        sid = environ.env.request.sid
        utils.create_or_update_user(user_id, user_name)
        utils.add_sid_for_user_id(user_id, sid)

        environ.env.join_room(user_id)
        environ.env.join_room(environ.env.request.sid)

    @staticmethod
    def publish_activity(arg: tuple) -> None:
        data, activity = arg
        user_id = activity.actor.id
        user_name = environ.env.session.get(SessionKeys.user_name.value)

        user_status = utils.get_user_status(user_id)
        activity_json = utils.activity_for_login(
            user_id, user_name, encode_attachments=False, user_status=user_status)

        environ.env.publish(activity_json, external=True)

    @staticmethod
    def reset_temp_session_values(arg: tuple):
        _, activity = arg
        for key in SessionKeys.temporary_keys.value:
            environ.env.auth.update_session_for_key(activity.actor.id, key, False)

    @staticmethod
    def set_user_online_if_not_previously_invisible(arg: tuple) -> None:
        data, activity = arg
        user_id = activity.actor.id
        user_status = utils.get_user_status(user_id)

        if utils.is_super_user(user_id) or utils.is_global_moderator(user_id):
            try:
                info_message = \
                    'op {} ({}) signed in; ' \
                    'user status is currently set to {}; ' \
                    'if not "3" (invisible), I will now change it to "1" (online)'
                info_message = info_message.format(
                    user_id, utils.get_user_name_for(user_id), user_status
                )
                logger.info(info_message)
            except NoSuchUserException:
                logger.error('no username found for op user {}'.format(user_id))
            except Exception as e:
                logger.error('exception while getting username for op {}: {}'.format(user_id, str(e)))
                logger.exception(e)
                environ.env.capture_exception(sys.exc_info())

        if user_status != UserKeys.STATUS_INVISIBLE:
            logger.info('setting user {} to online'.format(user_id))
            environ.env.db.set_user_online(user_id)
        else:
            # if login after server restart the cache value user:status:<user id> is non-existent, set to invisible
            environ.env.cache.set_user_invisible(user_id)

    @staticmethod
    def autojoin_rooms(arg: tuple) -> None:
        data, activity = arg

        if not str(environ.env.config.get(ConfigKeys.AUTOJOIN_ENABLED, 'false')).lower() in {'true', 'yes', '1', 'y'}:
            return

        try:
            room_acls = environ.env.db.get_room_acls_for_action(ApiActions.AUTOJOIN)
        except Exception as e:
            logger.error('could not get autojoin acls: {}'.format(str(e)))
            return

        for room_id, acls in room_acls.items():
            # needed for validation
            join_data = data.copy()
            join_data['target'] = {
                'id': room_id,
                'objectType': 'room'
            }

            is_valid, error_msg = validation.acl.validate_acl_for_action(
                activitystreams.parse(join_data),
                ApiTargets.ROOM,
                ApiActions.JOIN,
                acls
            )

            if not is_valid:
                continue

            join_data = ActivityBuilder.enrich({
                'verb': 'join',
                'actor': {
                    'id': activity.actor.id
                },
                'target': {
                    'id': room_id
                }
            })
            environ.env.observer.emit('on_join', (join_data, activitystreams.parse(join_data)))


@environ.env.observer.on('on_login')
def _on_login_set_user_online(arg: tuple) -> None:
    OnLoginHooks.set_user_online_if_not_previously_invisible(arg)
    OnLoginHooks.update_session_and_join_private_room(arg)
    OnLoginHooks.reset_temp_session_values(arg)
    OnLoginHooks.autojoin_rooms(arg)
    OnLoginHooks.publish_activity(arg)
