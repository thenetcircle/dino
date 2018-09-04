import logging

import sys
from zlib import crc32

from dino import environ
from dino import utils
from dino.config import SessionKeys
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

        if activity.actor.image is None:
            environ.env.session['image_url'] = ''
            environ.env.session[SessionKeys.image.value] = 'n'
        else:
            environ.env.session['image_url'] = activity.actor.image.url
            environ.env.session[SessionKeys.image.value] = 'y'

        utils.create_or_update_user(user_id, user_name)
        utils.add_sid_for_user_id(user_id, environ.env.request.sid)
        environ.env.join_room(user_id)
        environ.env.join_room(environ.env.request.sid)

    @staticmethod
    def publish_activity(arg: tuple) -> None:
        data, activity = arg
        user_id = activity.actor.id
        user_name = environ.env.session.get(SessionKeys.user_name.value)

        activity_json = utils.activity_for_login(user_id, user_name)
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
            environ.env.cache.add_to_multicast_on_login(user_id)


@environ.env.observer.on('on_login')
def _on_login_set_user_online(arg: tuple) -> None:
    OnLoginHooks.set_user_online_if_not_previously_invisible(arg)


@environ.env.observer.on('on_login')
def _on_login_update_session(arg: tuple) -> None:
    OnLoginHooks.update_session_and_join_private_room(arg)


@environ.env.observer.on('on_login')
def _on_login_reset_temp_session_values(arg: tuple) -> None:
    OnLoginHooks.reset_temp_session_values(arg)


@environ.env.observer.on('on_login')
def _on_login_publish_activity(arg: tuple) -> None:
    OnLoginHooks.publish_activity(arg)
