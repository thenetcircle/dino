import logging
import sys

from dino import environ
from dino import utils
from dino.config import SessionKeys
from dino.config import UserKeys
from dino.exceptions import NoSuchUserException


class OnStatusHooks(object):
    logger = logging.getLogger(__name__)

    @staticmethod
    def set_status(arg: tuple) -> None:
        data, activity = arg

        user_id = activity.actor.id
        user_name = environ.env.session.get(SessionKeys.user_name.value, None)
        image = environ.env.session.get(SessionKeys.image.value, '')
        status = activity.verb

        if user_name is None:
            try:
                user_name = utils.get_user_name_for(user_id)
            except NoSuchUserException:
                user_name = str(user_id)

        if not utils.is_valid_id(user_id):
            OnStatusHooks.logger.warning('got invalid user id for activity: {}'.format(str(data)))
            return

        if utils.is_super_user(user_id) or utils.is_global_moderator(user_id):
            OnStatusHooks.log_admin_activity(user_id, user_name, status)

        if status == 'online':
            OnStatusHooks.set_online(user_id, user_name, image)
        elif status == 'invisible':
            stage = 'status'
            if hasattr(activity.actor, 'summary'):
                stage = activity.actor.summary

            OnStatusHooks.set_invisible(user_id, user_name, stage=stage)
        elif status == 'visible':
            OnStatusHooks.set_visible(user_id, user_name)
        elif status == 'offline':
            OnStatusHooks.set_offline(user_id, user_name)
        elif status == 'away':
            OnStatusHooks.set_away(user_id)
        elif status == 'back':
            OnStatusHooks.set_back(user_id)

        if status in {"offline", "invisible"}:
            utils.add_last_online_at_to_event(data)

        # don't need to send an event for these statuses
        if status not in {'away', 'back'}:
            environ.env.publish(data, external=True)

    @staticmethod
    def log_admin_activity(user_id, user_name, status):
        try:
            info_message = \
                'op {} ({}) requested to change status to {}; user status is currently set to {}'.format(
                    user_id,
                    user_name,
                    status,
                    utils.get_user_status(user_id)
                )
            OnStatusHooks.logger.info(info_message)
        except NoSuchUserException:
            OnStatusHooks.logger.error('no username found for op user {}'.format(user_id))
        except Exception as e:
            OnStatusHooks.logger.error('exception while getting username for op {}: {}'.format(user_id, str(e)))
            OnStatusHooks.logger.exception(e)
            environ.env.capture_exception(sys.exc_info())

    @staticmethod
    def set_offline(user_id: str, user_name: str) -> None:
        OnStatusHooks.logger.info('setting user {} ({}) to offline'.format(
            user_id, user_name,
        ))
        environ.env.db.set_user_offline(user_id)
        activity_json = utils.activity_for_disconnect(user_id, user_name)
        rooms = utils.rooms_for_user(user_id)
        for room_id in rooms:
            environ.env.emit(
                'gn_user_disconnected', activity_json, room=room_id, broadcast=True,
                include_self=False, namespace='/ws')

    @staticmethod
    def set_away(user_id: str) -> None:
        user_status = utils.get_user_status(user_id, skip_cache=False)

        if user_status == UserKeys.STATUS_AVAILABLE:
            # TODO: should we sync this to solr? otherwise it's not searchable
            #  if not, saving to redis should be enough
            OnStatusHooks.logger.info(f"setting user {user_id} to away (was online)")
            environ.env.cache.set_user_away(user_id)

    @staticmethod
    def set_back(user_id: str) -> None:
        user_status = utils.get_user_status(user_id, skip_cache=False)

        if user_status == UserKeys.STATUS_AWAY:
            # TODO: should we sync this to solr? otherwise it's not searchable
            #  if not, saving to redis should be enough
            OnStatusHooks.logger.info(f"setting user {user_id} back to online (was away)")
            environ.env.cache.set_user_online(user_id)

    @staticmethod
    def set_visible(user_id: str, user_name: str) -> None:
        user_status = utils.get_user_status(user_id, skip_cache=True)
        if user_status in {UserKeys.STATUS_AVAILABLE, UserKeys.STATUS_CHAT}:
            return

        # status is UserKeys.STATUS_VISIBLE, but is in multicast so the user is online
        if environ.env.cache.user_is_in_multicast(user_id):
            OnStatusHooks.logger.info(
                'setting user {} ({}) to visible (online), was invisible (online)'.format(user_id, user_name))
            OnStatusHooks.set_online(user_id, user_name)

        # otherwise status is UserKeys.STATUS_INVISIBLE, but if not in multicast the user is offline
        # TODO: when choosing to login invisibly, this is called before the user connects to dino, so should NOT do set_offline()
        # TODO: should visible login call set_status with 'online' or 'visible'?
        else:
            OnStatusHooks.logger.info(
                'setting user {} ({}) to visible (offline), was invisible (offline)'.format(user_id, user_name))
            OnStatusHooks.set_offline(user_id, user_name)

    @staticmethod
    def set_invisible(user_id: str, user_name: str, stage: str) -> None:
        user_status = utils.get_user_status(user_id)

        # no need to set it again if already invisible
        if user_status == UserKeys.STATUS_INVISIBLE:
            return

        OnStatusHooks.logger.info('setting user {} ({}) to invisible'.format(
            user_id, user_name,
        ))

        # when logging in as 'invisible', the rest call can happen after ws
        # logs in, in which case we don't want to update last_online
        if stage == 'login':
            is_offline = True
        else:
            is_offline = not utils.user_is_online(user_id)

        environ.env.db.set_user_invisible(user_id, is_offline=is_offline)

        if is_offline:
            # nothing more to do if offline already
            return

        disconnect_activity = utils.activity_for_disconnect(user_id, user_name)

        rooms = utils.rooms_for_user(user_id)
        for room_id in rooms:
            admins_in_room = environ.env.db.get_admins_in_room(room_id, user_id)
            if admins_in_room is None or len(admins_in_room) == 0:
                environ.env.emit('gn_user_disconnected', disconnect_activity, room=room_id, broadcast=True,
                                 include_self=False, namespace='/ws')
                continue

            users_in_room = utils.get_users_in_room(room_id)
            for other_user_id, _ in users_in_room.items():
                if other_user_id in admins_in_room:
                    continue
                environ.env.emit(
                    'gn_user_disconnected', disconnect_activity, room=other_user_id, broadcast=True,
                    include_self=False, namespace='/ws')

            invisible_activity = utils.activity_for_going_invisible(user_id)
            for admin_id in admins_in_room:
                environ.env.emit(
                    'gn_user_invisible', invisible_activity, room=admin_id, broadcast=False, namespace='/ws')

    @staticmethod
    def set_online(user_id: str, user_name: str, image: str = '') -> None:
        was_invisible = utils.user_is_invisible(user_id)
        OnStatusHooks.logger.info('setting user {} ({}) online (was invisible before? {})'.format(
            user_id, user_name, was_invisible
        ))
        environ.env.db.set_user_online(user_id)
        rooms = utils.rooms_for_user(user_id)

        if not was_invisible:
            for room_id in rooms:
                room_name = utils.get_room_name(room_id)
                join_activity = utils.activity_for_user_joined(user_id, user_name, room_id, room_name, image)
                environ.env.emit(
                    'gn_user_joined', join_activity, room=room_id, broadcast=True,
                    include_self=False, namespace='/ws')
            return

        visible_activity = utils.activity_for_going_visible(user_id)
        for room_id in rooms:
            room_name = utils.get_room_name(room_id)
            join_activity = utils.activity_for_user_joined(user_id, user_name, room_id, room_name, image)
            admins_in_room = environ.env.db.get_admins_in_room(room_id, user_id)

            if admins_in_room is None or len(admins_in_room) == 0:
                environ.env.emit(
                    'gn_user_joined', join_activity, room=room_id, broadcast=True,
                    include_self=False, namespace='/ws')
                continue

            users_in_room = utils.get_users_in_room(room_id).copy()
            for user_id_in_room, _ in users_in_room.items():
                if user_id_in_room in admins_in_room:
                    continue
                environ.env.emit(
                    'gn_user_joined', join_activity, room=user_id_in_room, broadcast=True,
                    include_self=False, namespace='/ws')

            for admin_id in admins_in_room:
                environ.env.emit(
                    'gn_user_visible', visible_activity, room=admin_id, broadcast=False, namespace='/ws')


@environ.env.observer.on('on_status')
def _on_status_set_status(arg: tuple) -> None:
    OnStatusHooks.set_status(arg)
