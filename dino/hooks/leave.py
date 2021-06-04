from dino.exceptions import NoSuchRoomException

from dino import environ
from dino import utils
from dino.config import UserKeys


class OnLeaveHooks(object):
    @staticmethod
    def leave_room(arg: tuple) -> None:
        data, activity = arg

        user_id = activity.actor.id
        room_id = activity.target.id
        user_name = utils.get_user_name_from_activity_or_session(user_id, activity, environ.env)

        try:
            room_name = utils.get_room_name(room_id)
        except NoSuchRoomException:
            room_name = '[removed]'

        namespace = "/ws"
        is_out_of_scope = False

        # if specified, this is a REST api request, so we need to leave for all sids
        if hasattr(activity.actor, "content") and activity.actor.content is not None:
            sids = activity.actor.content.split(",")
            is_out_of_scope = True

        # otherwise, this is a leave request from socket api, so only leave with this sid
        else:
            utils.remove_sid_for_user_in_room(user_id, room_id, environ.env.request.sid)

            # multi-login, can be in same room with another session still
            sids = utils.sids_for_user_in_room(user_id, room_id)
            if sids is not None and len(sids) > 0:
                if len(sids) > 1 or next(iter(sids)) != environ.env.request.sid:
                    return

            utils.remove_user_from_room(user_id, user_name, room_id)

        # REST request to leave room, not from socket api
        if is_out_of_scope:
            skip_db_leave = False
            for sid in sids:
                utils.remove_user_from_room(
                    user_id,
                    user_name,
                    room_id,
                    sid=sid,
                    namespace=namespace,
                    is_out_of_scope=is_out_of_scope,
                    skip_db_leave=skip_db_leave
                )

                # skip deleting after first time, only need to delete once in multi-sid leaves
                skip_db_leave = True

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

        if is_out_of_scope:
            environ.env.out_of_scope_emit(
                'gn_user_left', activity_left, room=room_id,
                broadcast=True,
                include_self=True,  # otherwise it will try to get the sid from the flask request (which doesn't exist)
                namespace='/ws'
            )

            # send one to the user's private room as well, since the user already
            # left the room the above event won't be sent to the user
            environ.env.out_of_scope_emit(
                'gn_user_left', activity_left, room=user_id,
                broadcast=True, include_self=True, namespace='/ws'
            )
        else:
            environ.env.emit(
                'gn_user_left', activity_left, room=room_id,
                broadcast=True, include_self=False, namespace='/ws'
            )

        utils.check_if_remove_room_empty(activity, user_name=user_name, is_delayed_removal=False)


@environ.env.observer.on('on_leave')
def _on_leave_leave_room(arg: tuple) -> None:
    OnLeaveHooks.leave_room(arg)
