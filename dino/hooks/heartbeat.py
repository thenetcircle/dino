import logging
import sys
import traceback

from dino import environ
from dino import utils
from dino.config import SessionKeys
from dino.config import UserKeys
from dino.exceptions import NoSuchUserException

logger = logging.getLogger(__name__)


class OnHeartbeatHooks(object):
    @staticmethod
    def update_session(arg: tuple) -> None:
        data, activity = arg
        user_id = activity.actor.id
        user_name = activity.actor.display_name
        sid = 'hb-{}'.format(user_id)
        utils.create_or_update_user(user_id, user_name)
        utils.add_sid_for_user_id(user_id, sid)

    @staticmethod
    def publish_activity(arg: tuple) -> None:
        data, activity = arg
        user_id = activity.actor.id
        user_name = activity.actor.display_name

        # only publish 'login' activity on the first heartbeat
        if environ.env.heartbeat.has_heartbeat(user_id):
            return

        activity_json = utils.activity_for_login(user_id, user_name, encode_attachments=False, heartbeat_sid=True)
        environ.env.publish(activity_json, external=True)

    @staticmethod
    def set_user_online_if_not_previously_invisible(arg: tuple) -> None:
        data, activity = arg
        user_id = activity.actor.id
        user_status = utils.get_user_status(user_id)
        environ.env.cache.check_heartbeat(user_id)

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
            environ.env.db.set_user_online(user_id)
        else:
            # if heartbeat after server restart the cache value user:status:<user id> is non-existent, set to invisible
            environ.env.cache.set_user_invisible(user_id)


@environ.env.observer.on('on_heartbeat')
def _on_heartbeat_publish_activity(arg: tuple) -> None:
    OnHeartbeatHooks.update_session(arg)

    # need to publish before setting as online, as we won't publish if already online
    OnHeartbeatHooks.publish_activity(arg)

    OnHeartbeatHooks.set_user_online_if_not_previously_invisible(arg)
