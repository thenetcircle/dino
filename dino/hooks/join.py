# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import eventlet
from dino.exceptions import NoSuchRoomException

from dino import environ
from dino import utils
from dino.config import SessionKeys, ConfigKeys
from dino.config import UserKeys
from dino.utils.decorators import timeit

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


class OnJoinHooks(object):
    @staticmethod
    def join_room(arg: tuple) -> None:
        data, activity = arg
        room_id = activity.target.id
        user_id = activity.actor.id

        sids = [None]
        namespace = None

        if hasattr(activity.actor, "content"):
            sids = activity.actor.content
            sids = sids.split(",")

        if hasattr(activity.actor, "url"):
            namespace = activity.actor.url

        user_name = environ.env.session.get(SessionKeys.user_name.value)
        room_name = utils.get_room_name(room_id)

        if user_name is None:
            environ.env.db.get_user_name(user_id)

        # for the first session (or the only session), we want to add a
        # row to the db, but not for any other sessions that are open
        skip_db_join = False

        for sid in sids:
            try:
                utils.join_the_room(
                    user_id,
                    user_name,
                    room_id,
                    room_name,
                    skip_db_join=skip_db_join,
                    sid=sid,
                    namespace=namespace
                )

                # for any other open session, we just want to tell flask to join the
                # session in the room, but not add another row in the db for it
                skip_db_join = True

            except NoSuchRoomException:
                logger.error('tried to join non-existing room "{}" ({})'.format(room_id, room_name))

        if environ.env.config.get(ConfigKeys.COUNT_CUMULATIVE_JOINS, default=False):
            try:
                environ.env.db.increase_join_count(room_id)
            except Exception as e:
                logger.error('could not increase cumulative room joins: {}'.format(str(e)))

    @staticmethod
    def emit_join_event(activity, user_id, user_name, image) -> None:
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
        environ.env.out_of_scope_emit('gn_user_joined', activity_json, room=room_id, broadcast=True, namespace='/ws')
        environ.env.publish(activity_json, external=True)


@environ.env.observer.on('on_join')
@timeit(logger, 'on_join_hooks')
def _on_join_join_room(arg: tuple) -> None:
    OnJoinHooks.join_room(arg)


@environ.env.observer.on('on_join')
def _on_join_emit_join_event(arg: tuple) -> None:
    user_name = environ.env.session.get(SessionKeys.user_name.value)
    user_id = environ.env.session.get(SessionKeys.user_id.value)
    image = environ.env.session.get(SessionKeys.image.value, '')
    eventlet.spawn(OnJoinHooks.emit_join_event, arg[1], user_id, user_name, image)
