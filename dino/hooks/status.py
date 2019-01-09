import logging
import sys

from dino import environ
from dino import utils
from dino.config import SessionKeys
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

        if not utils.is_valid_id(user_id):
            OnStatusHooks.logger.warning('got invalid id on disconnect for act: {}'.format(str(activity.id)))
            # TODO: sentry
            return

        if utils.is_super_user(user_id) or utils.is_global_moderator(user_id):
            try:
                info_message = \
                    'op {} ({}) requested to change status to {}; user status is currently set to {}'.format(
                        user_id,
                        utils.get_user_name_for(user_id),
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

        if status == 'online':
            OnStatusHooks.set_online(user_id, user_name, image)

        elif status == 'invisible':
            OnStatusHooks.set_invisible(user_id, user_name)

        elif status == 'offline':
            OnStatusHooks.set_offline(user_id, user_name)

        environ.env.publish(data, external=True)

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
    def set_invisible(user_id: str, user_name: str) -> None:
        OnStatusHooks.logger.info('setting user {} ({}) to invisible'.format(
            user_id, user_name,
        ))
        environ.env.db.set_user_invisible(user_id)
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
    def set_online(user_id: str, user_name: str, image: str) -> None:
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
