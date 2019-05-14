from dino.exceptions import NoSuchRoomException

from dino import environ
from dino import utils
from dino.config import UserKeys


class OnLeaveHooks(object):
    @staticmethod
    def leave_room(arg: tuple) -> None:
        data, activity = arg

        user_id = activity.actor.id
        user_name = activity.actor.display_name
        room_id = activity.target.id

        try:
            room_name = utils.get_room_name(room_id)
        except NoSuchRoomException:
            room_name = '[removed]'

        utils.remove_sid_for_user_in_room(user_id, room_id, environ.env.request.sid)

        # multi-login, can be in same room as another session
        sids = utils.sids_for_user_in_room(user_id, room_id)
        if sids is not None and len(sids) > 0:
            return

        utils.remove_user_from_room(user_id, user_name, room_id)

        # if invisible, only send 'invisible' leave to admins in the room
        if utils.get_user_status(user_id) == UserKeys.STATUS_INVISIBLE:
            admins_in_room = environ.env.db.get_admins_in_room(room_id, user_id)
            if admins_in_room is None or len(admins_in_room) == 0:
                return

            activity_left = utils.activity_for_leave(user_id, user_name, room_id, room_name)
            for admin_id in admins_in_room:
                environ.env.out_of_scope_emit(
                    'gn_user_left', activity_left, room=admin_id, broadcast=False, namespace='/ws')
            return

        activity_left = utils.activity_for_leave(user_id, user_name, room_id, room_name)
        environ.env.emit(
            'gn_user_left', activity_left, room=room_id, broadcast=True, include_self=False, namespace='/ws')
        utils.check_if_should_remove_room(data, activity)


@environ.env.observer.on('on_leave')
def _on_leave_leave_room(arg: tuple) -> None:
    OnLeaveHooks.leave_room(arg)
