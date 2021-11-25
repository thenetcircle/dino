import logging
import eventlet
from dino.exceptions import NoSuchRoomException

from dino import environ
from dino import utils
from dino.config import SessionKeys, ConfigKeys
from dino.config import UserKeys
from dino.utils.decorators import timeit

logger = logging.getLogger(__name__)


def is_autojoin(activity):
    # no need to emit events for autojoin
    try:
        return activity.target.content == 'autojoin'
    except KeyError:
        return False


class OnJoinHooks(object):
    @staticmethod
    def join_room(arg: tuple) -> None:
        data, activity = arg
        room_id = activity.target.id
        user_id = activity.actor.id

        sids = [None]
        namespace = "/ws"

        if hasattr(activity.actor, "content") and activity.actor.content is not None:
            sids = activity.actor.content
            sids = sids.split(",")

        if hasattr(activity.actor, "url"):
            namespace = activity.actor.url

        user_name = utils.get_user_name_from_activity_or_session(user_id, activity, environ.env)
        room_name = utils.get_room_name(room_id)

        # for the first session (or the only session), we want to add a
        # row to the db, but not for any other sessions that are open
        skip_db_join = False

        # also don't need to update the db if it's wio autojoin
        if environ.env.node == 'wio':
            skip_db_join = True

        # joins from rest api is outside the flask request scope
        is_out_of_scope = False
        if hasattr(activity.target, "content"):
            is_out_of_scope = activity.target.content == "out_of_scope"

        for sid in sids:
            logger.info("user {} ({}) is joining room {} ({}) with sid {} on ns {} (skip db? {})".format(
                user_id, user_name, room_id, room_name, sid, namespace, skip_db_join
            ))

            try:
                utils.join_the_room(
                    user_id,
                    user_name,
                    room_id,
                    room_name,
                    skip_db_join=skip_db_join,
                    sid=sid,
                    namespace=namespace,
                    is_out_of_scope=is_out_of_scope
                )

                # for any other open session, we just want to tell flask to join the
                # session in the room, but not add another row in the db for it
                skip_db_join = True

            except NoSuchRoomException:
                logger.error('tried to join non-existing room "{}" ({})'.format(room_id, room_name))

        if environ.env.config.get(ConfigKeys.COUNT_CUMULATIVE_JOINS, default=False):
            try:
                environ.env.db.increase_join_count(room_id, room_name)
            except Exception as e:
                logger.error('could not increase cumulative room joins: {}'.format(str(e)))

    @staticmethod
    def emit_join_event(activity, user_id, user_name, image) -> None:
        # no need if it's wio
        if environ.env.node == 'wio':
            return

        room_id = activity.target.id
        room_name = utils.get_room_name(room_id)

        # if invisible, only sent 'invisible' join to admins in the room
        if utils.get_user_status(user_id) == UserKeys.STATUS_INVISIBLE:
            admins_in_room = environ.env.db.get_admins_in_room(room_id, user_id)
            if admins_in_room is None or len(admins_in_room) == 0:
                return

            room_name = utils.get_room_name(room_id)
            activity_json = utils.activity_for_user_joined_invisibly(user_id, user_name, room_id, room_name, image)
            for admin_id in admins_in_room:
                environ.env.out_of_scope_emit(
                    'gn_user_joined', activity_json, room=admin_id, broadcast=False, namespace='/ws')
            return

        activity_json = utils.activity_for_user_joined(user_id, user_name, room_id, room_name, image)
        environ.env.out_of_scope_emit('gn_user_joined', activity_json, json=True, room=room_id, broadcast=True, namespace='/ws')
        environ.env.publish(activity_json, external=True)


@environ.env.observer.on('on_join')
@timeit(logger, 'on_join_hooks')
def _on_join_join_room(arg: tuple) -> None:
    OnJoinHooks.join_room(arg)


@environ.env.observer.on('on_join')
def _on_join_emit_join_event(arg: tuple) -> None:
    activity = arg[1]

    image = ""
    user_name = None
    user_id = None

    try:
        image = environ.env.session.get(SessionKeys.image.value, '')
    except Exception:
        pass

    if hasattr(activity, "actor"):
        if hasattr(activity.actor, "id"):
            user_id = activity.actor.id
        if hasattr(activity.actor, "display_name"):
            user_name = utils.b64d(activity.actor.display_name)

    if user_id is None:
        user_id = environ.env.session.get(SessionKeys.user_id.value)
    if user_name is None:
        user_name = environ.env.session.get(SessionKeys.user_name.value)

    eventlet.spawn(OnJoinHooks.emit_join_event, activity, user_id, user_name, image)
