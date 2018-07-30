import logging
import traceback

from dino.wio import environ
from dino.wio import utils
from dino.config import SessionKeys
from dino.config import UserKeys
from dino.exceptions import NoSuchUserException

logger = logging.getLogger(__name__)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class OnDisconnectHooks(object):
    @staticmethod
    def handle_disconnect(arg: tuple):
        def set_user_offline():
            try:
                user_id = activity.actor.id
                if not utils.is_valid_id(user_id):
                    logger.warning('got invalid id on disconnect for act: {}'.format(str(activity.id)))
                    return

                current_sid = environ.env.request.sid
                environ.env.db.remove_sid_for_user(user_id, current_sid)

                all_sids = utils.get_sids_for_user_id(user_id)
                # if the user still has another session up we don't set the user as offline
                if all_sids is not None and len(all_sids) > 0:
                    logger.debug('when setting user offline, found other sids: [%s]' % ','.join(all_sids))
                    return

                if utils.get_user_status(user_id) != UserKeys.STATUS_INVISIBLE:
                    environ.env.db.set_user_offline(user_id)
            except Exception as e:
                logger.error('could not set user offline: %s' % str(e))
                logger.debug('request for failed set_user_offline(): %s' % str(data))
                logger.exception(traceback.format_exc())

        def leave_private_room():
            try:
                user_id = activity.actor.id
                user_name = environ.env.session.get(SessionKeys.user_name.value)
                current_sid = environ.env.request.sid
                logger.debug('a user disconnected [id: "%s", name: "%s", sid: "%s"]' % (user_id, user_name, current_sid))

                if user_id is None or len(user_id.strip()) == 0:
                    return
                environ.env.leave_room(current_sid)
                environ.env.db.remove_sid_for_user(user_id, current_sid)

                all_sids = utils.get_sids_for_user_id(user_id)
                if all_sids is None:
                    all_sids = list()
                all_sids = all_sids.copy()

                if len(all_sids) == 0 or (current_sid in all_sids and len(all_sids) == 1):
                    environ.env.leave_room(user_id)
                    environ.env.db.reset_sids_for_user(user_id)
                    for key in SessionKeys.temporary_keys.value:
                        environ.env.auth.update_session_for_key(activity.actor.id, key, False)

            except Exception as e:
                logger.error('could not leave private room: %s' % str(e))
                logger.debug('request for failed leave_private_room(): %s' % str(data))
                logger.exception(traceback.format_exc())

        def emit_disconnect_event() -> None:
            try:
                user_id = activity.actor.id
                user_name = environ.env.session.get(SessionKeys.user_name.value)
                if user_name is None or len(user_name.strip()) == 0:
                    try:
                        user_name = utils.get_user_name_for(user_id)
                    except NoSuchUserException:
                        user_name = '<unknown>'

                if user_id is None or user_id == 'None':
                    logger.warning('blank user_id, ignoring disconnect event')
                    return

                all_sids = utils.get_sids_for_user_id(user_id)
                if all_sids is None:
                    all_sids = list()

                logger.debug(
                    'sid %s disconnected, all_sids: [%s] for user %s (%s)' % (
                        environ.env.request.sid, ','.join(all_sids), user_id, user_name))

                # if the user still has another session up we don't send disconnect event
                if all_sids is not None and len(all_sids) > 0:
                    return

                activity_json = utils.activity_for_disconnect(user_id, user_name)
                environ.env.publish(activity_json, external=True)
            except Exception as e:
                logger.error('could not emit disconnect event: %s' % str(e))
                logger.debug('request for failed emit_disconnect_event(): %s' % str(data))
                logger.exception(traceback.format_exc())

        data, activity = arg

        leave_private_room()
        emit_disconnect_event()
        set_user_offline()


@environ.env.observer.on('on_disconnect')
def _on_disconnect_handle_disconnect(arg: tuple) -> None:
    OnDisconnectHooks.handle_disconnect(arg)
