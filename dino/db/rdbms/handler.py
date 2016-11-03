#!/usr/bin/env python

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

from datetime import datetime
from typing import Union
from uuid import uuid4 as uuid

from dino.config import ConfigKeys
from dino.config import RoleKeys
from dino.config import UserKeys
from dino.config import ApiTargets
from dino.config import ApiActions

from dino.validation.acl import AclValidator

from dino.db import IDatabase
from dino.db.rdbms.dbman import Database
from dino.db.rdbms.mock import MockDatabase
from dino.db.rdbms.models import ChannelRoles
from dino.db.rdbms.models import GlobalRoles
from dino.db.rdbms.models import Channels
from dino.db.rdbms.models import RoomRoles
from dino.db.rdbms.models import Rooms
from dino.db.rdbms.models import Acls
from dino.db.rdbms.models import AclConfigs
from dino.db.rdbms.models import UserStatus
from dino.db.rdbms.models import Users
from dino.db.rdbms.models import LastReads
from dino.db.rdbms.models import Bans

from dino.exceptions import ChannelExistsException
from dino.exceptions import NoSuchChannelException
from dino.exceptions import NoSuchRoomException
from dino.exceptions import RoomExistsException
from dino.exceptions import RoomNameExistsForChannelException
from dino.exceptions import NoChannelFoundException
from dino.exceptions import UserExistsException
from dino.exceptions import NoSuchUserException
from dino.exceptions import InvalidAclTypeException
from dino.exceptions import InvalidAclValueException
from dino.exceptions import AclValueNotFoundException
from dino.exceptions import EmptyChannelNameException
from dino.exceptions import EmptyRoomNameException
from dino.exceptions import ChannelNameExistsException
from dino.exceptions import ValidationException
from dino.exceptions import InvalidApiActionException

from functools import wraps
from zope.interface import implementer
import logging

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


def with_session(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        session = DatabaseRdbms.db.Session()
        try:
            _self = args[0]
            _self.__dict__.update({'session': session})
            return view_func(*args, **kwargs)
        except:
            session.rollback()
            raise
        finally:
            session.close()

    return wrapped


@implementer(IDatabase)
class DatabaseRdbms(object):
    def __init__(self, env):
        self.env = env
        self.session = None
        if self.env.config.get(ConfigKeys.TESTING, False):
            DatabaseRdbms.db = MockDatabase()
        else:
            DatabaseRdbms.db = Database(env)

    @with_session
    def _session(self):
        return self.session

    def room_exists(self, channel_id: str, room_id: str) -> bool:
        @with_session
        def _room_exists(self):
            rooms = self.session.query(Rooms) \
                .filter(Rooms.uuid == room_id) \
                .all()

            exists = len(rooms) > 0
            if exists:
                self.env.cache.set_room_exists(channel_id, room_id, rooms[0].name)
            return exists

        exists = self.env.cache.get_room_exists(channel_id, room_id)
        if exists is not None:
            return exists
        return _room_exists(self)

    def get_user_status(self, user_id: str) -> str:
        @with_session
        def _get_user_status(self):
            status = self.session.query(UserStatus).filter(Users.uuid == user_id).first()
            if status is None:
                return UserKeys.STATUS_UNAVAILABLE
            return status.status

        status = self.env.cache.get_user_status(user_id)
        if status is not None:
            return status
        return _get_user_status(self)

    def set_user_invisible(self, user_id: str) -> None:
        @with_session
        def _set_user_invisible(self):
            self.env.cache.set_user_invisible(user_id)
            self.session.query(UserStatus).filter_by(uuid=user_id).update({'status': UserKeys.STATUS_INVISIBLE})
            self.session.commit()

        if self.env.cache.user_is_invisible(user_id):
            return
        _set_user_invisible(self)

    def set_user_offline(self, user_id: str) -> None:
        @with_session
        def _set_user_offline(self):
            self.env.cache.set_user_offline(user_id)
            status = self.session.query(UserStatus).filter_by(uuid=user_id).first()
            self.session.delete(status)
            self.session.commit()

        if self.env.cache.user_is_offline(user_id):
            return
        _set_user_offline()

    def set_user_online(self, user_id: str) -> None:
        @with_session
        def _set_user_online(self):
            self.env.cache.set_user_online(user_id)
            self.session.query(UserStatus).filter_by(uuid=user_id).update({'status': UserKeys.STATUS_AVAILABLE})
            self.session.commit()

        if self.env.cache.user_is_online(user_id):
            return
        _set_user_online(self)

    @with_session
    def rooms_for_user(self, user_id: str = None) -> dict:
        rows = self.session.query(Rooms).join(Rooms.users).filter(Users.uuid == user_id).all()
        rooms = dict()
        for row in rows:
            rooms[row.uuid] = row.name
        return rooms

    @with_session
    def rooms_for_channel(self, channel_id) -> dict:
        rows = self.session.query(Rooms).join(Rooms.channel).filter(Channels.uuid == channel_id).all()
        rooms = dict()
        for row in rows:
            rooms[row.uuid] = row.name
        return rooms

    def users_in_room(self, room_id: str) -> dict:
        @with_session
        def _users_in_room(self) -> dict:
            rows = self.session.query(Rooms).join(Rooms.users).filter(Rooms.uuid == room_id).all()
            users = dict()
            for row in rows:
                for user in row.users:
                    users[user.uuid] = user.name
            return users

        if self.channel_for_room(room_id) is None:
            raise NoSuchRoomException(room_id)
        return _users_in_room(self)

    def room_contains(self, room_id: str, user_id: str) -> bool:
        try:
            if self.channel_for_room(room_id) is None:
                raise NoSuchRoomException(room_id)
        except NoChannelFoundException:
            raise NoSuchRoomException(room_id)

        return room_id in self.rooms_for_user(user_id)

    @with_session
    def remove_current_rooms_for_user(self, user_id: str) -> None:
        user = self.session.query(Users).filter(Users.uuid == user_id).first()
        if user is None:
            return

        if user.rooms is not None and len(user.rooms) > 0:
            for room in user.rooms:
                user.rooms.remove(room)
        self.session.commit()

    @with_session
    def get_channels(self) -> dict:
        rows = self.session.query(Channels).all()
        channels = dict()
        for row in rows:
            channels[row.uuid] = row.name
        return channels

    @with_session
    def channel_name_exists(self, channel_name: str) -> bool:
        rows = self.session.query(Channels).filter(Channels.name == channel_name).all()
        return rows is not None and len(rows) > 0

    def room_name_exists(self, channel_id, room_name: str) -> bool:
        @with_session
        def _room_name_exists(self):
            rows = self.session.query(Rooms).filter(Rooms.name == room_name).all()
            exists = len(rows) > 0

            # only set in cache if actually exists, otherwise duplicates could be created
            if exists:
                self.env.cache.set_room_id_for_name(channel_id, room_name, rows[0].uuid)

            return exists

        exists = self.env.cache.get_room_id_for_name(channel_id, room_name)
        if exists is not None:
            return exists

        return _room_name_exists(self)

    def rename_channel(self, channel_id: str, channel_name: str) -> None:
        @with_session
        def _rename_channel(self):
            channel = self.session.query(Channels).filter(Channels.uuid == channel_id).first()
            if channel is None:
                raise NoSuchChannelException(channel_id)

            if channel.name == channel_name.strip():
                return
            channel.name = channel_name
            self.session.commit()

        if channel_name is None or len(channel_name.strip()) == 0:
            raise EmptyChannelNameException(channel_id)

        channel_name = channel_name.strip()
        if self.channel_name_exists(channel_name):
            raise ChannelNameExistsException(channel_name)
        _rename_channel(self)

    def rename_room(self, channel_id: str, room_id: str, room_name: str) -> None:
        @with_session
        def _rename_room(self):
            room = self.session.query(Rooms).filter(Rooms.uuid == room_id).first()
            if room is None:
                raise NoSuchRoomException(room_id)

            if room.name == room_name.strip():
                return
            room.name = room_name
            self.session.commit()

        if room_name is None or len(room_name.strip()) == 0:
            raise EmptyRoomNameException(room_id)

        room_name = room_name.strip()
        if self.room_name_exists(channel_id, room_name):
            raise RoomNameExistsForChannelException(channel_id, room_name)
        _rename_room(self)

    def channel_for_room(self, room_id: str) -> str:
        @with_session
        def _channel_for_room(self):
            room = self.session\
                .query(Rooms)\
                .join(Rooms.channel)\
                .filter(Rooms.uuid == room_id)\
                .first()

            if room is None or room.channel is None:
                raise NoChannelFoundException(room_id)
            return room.channel.uuid

        value = self.env.cache.get_channel_for_room(room_id)
        if value is not None:
            return value

        return _channel_for_room(self)

    def channel_exists(self, channel_id) -> bool:
        @with_session
        def _channel_exists(self):
            rows = self.session.query(Channels).filter(Channels.uuid == channel_id).all()
            exists = len(rows) > 0

            # only set in cache if actually exists, otherwise duplicates could be created
            if exists:
                self.env.cache.set_channel_exists(channel_id)

            return exists

        exists = self.env.cache.get_channel_exists(channel_id)
        if exists is not None:
            return exists
        return _channel_exists(self)

    def create_channel(self, channel_name, channel_id, user_id):
        @with_session
        def _create_channel(self):
            channel = Channels()
            channel.uuid = channel_id
            channel.name = channel_name
            channel.created = datetime.utcnow()
            self.session.add(channel)

            role = ChannelRoles()
            role.channel = channel
            role.user_id = user_id
            role.roles = RoleKeys.OWNER
            self.session.add(role)

            channel.roles.append(role)
            self.session.add(channel)
            self.session.commit()

            self.env.cache.set_channel_exists(channel_id)

        if channel_name is None or len(channel_name.strip()) == 0:
            raise EmptyChannelNameException(channel_id)

        if self.channel_exists(channel_id):
            raise ChannelExistsException(channel_id)
        _create_channel(self)

    def create_room(self, room_name: str, room_id: str, channel_id: str, user_id: str, user_name: str) -> None:
        @with_session
        def _create_room(self):
            channel = self.session.query(Channels).filter(Channels.uuid == channel_id).first()
            if channel is None:
                raise NoSuchChannelException(channel_id)

            room = Rooms()
            room.uuid = room_id
            room.name = room_name
            room.channel = channel
            room.created = datetime.utcnow()
            self.session.add(room)

            role = RoomRoles()
            role.room = room
            role.user_id = user_id
            role.roles = RoleKeys.OWNER
            self.session.add(role)

            room.roles.append(role)
            self.session.add(role)

            channel.rooms.append(room)
            self.session.add(channel)
            self.session.commit()

        if room_name is None or len(room_name.strip()) == 0:
            raise EmptyRoomNameException(room_id)

        if self.room_exists(channel_id, room_id):
            raise RoomExistsException(room_id)

        if self.room_name_exists(channel_id, room_name):
            raise RoomNameExistsForChannelException(channel_id, room_name)
        _create_room(self)

    @with_session
    def remove_room(self, channel_id: str, room_id: str) -> None:
        room = self.session\
            .query(Rooms)\
            .join(Rooms.channel)\
            .filter(Rooms.uuid == room_id)\
            .filter(Channels.uuid == channel_id)\
            .first()

        if room is None:
            raise RoomExistsException(room_id)

        roles = self.session.query(RoomRoles).join(RoomRoles.room).filter(Rooms.uuid == room_id).all()
        if roles is not None and len(roles) > 0:
            for role in roles:
                self.session.delete(role)

        self.session.delete(room)
        self.session.commit()

    @with_session
    def leave_room(self, user_id: str, room_id: str) -> None:
        room = self.session.query(Rooms).filter(Rooms.uuid == room_id).first()
        if room is None:
            raise NoSuchRoomException(room_id)

        user = self.session.query(Users)\
            .join(Users.rooms)\
            .filter(Users.uuid == user_id)\
            .filter(Rooms.uuid == room_id)\
            .first()

        if user is None:
            # user is not in the room, so nothing to do
            return

        room.users.remove(user)
        self.session.commit()

    @with_session
    def join_room(self, user_id: str, user_name: str, room_id: str, room_name: str) -> None:
        room = self.session.query(Rooms).filter(Rooms.uuid == room_id).first()
        if room is None:
            raise NoSuchRoomException(room_id)

        user = self.session.query(Users).filter(Users.uuid == user_id).first()
        if user is None:
            user = Users()
            user.uuid = user_id
            user.name = user_name
            self.session.add(user)

        user.rooms.append(room)
        self.session.add(room)

        room.users.append(user)
        self.session.add(room)
        self.session.commit()

    def _object_has_role_for_user(self, obj: Union[Rooms, Channels], the_role: str, user_id: str) -> bool:
        if obj is None:
            return False

        found_role = None
        for role in obj.roles:
            if role.user_id == user_id:
                found_role = role
                break

        if found_role is None:
            return False
        if found_role.roles is None or found_role.roles == '':
            return False

        return the_role in set(found_role.roles.split(','))

    @with_session
    def _add_global_role(self, user_id: str, role: str):
        global_role = self.session.query(GlobalRoles).filter(GlobalRoles.user_id == user_id).first()
        if global_role is None:
            global_role = GlobalRoles()
            global_role.user_id = user_id
            global_role.roles = role
            self.session.add(global_role)
            self.session.commit()
            return

        roles = set(global_role.roles.split(','))
        if role in roles:
            return

        roles.add(role)
        global_role.roles = ','.join(roles)

    @with_session
    def _remove_global_role(self, user_id: str, role: str):
        global_role = self.session.query(GlobalRoles).filter(GlobalRoles.user_id == user_id).first()
        if global_role is None:
            return

        roles = set(global_role.roles.split(','))
        if role not in roles:
            return

        roles.remove(role)
        global_role.roles = ','.join(roles)
        self.session.commit()

    @with_session
    def _has_global_role(self, user_id: str, role: str):
        global_role = self.session.query(GlobalRoles).filter(GlobalRoles.user_id == user_id).first()
        if global_role is None:
            return False

        roles = set(global_role.roles.split(','))
        return role in roles

    @with_session
    def _room_has_role_for_user(self, the_role: str, room_id: str, user_id: str) -> bool:
        # TODO: cache
        room = self.session.query(Rooms).join(Rooms.roles).filter(Rooms.uuid == room_id).first()
        return self._object_has_role_for_user(room, the_role, user_id)

    @with_session
    def _channel_has_role_for_user(self, the_role: str, channel_id: str, user_id: str) -> bool:
        # TODO: cache
        channel = self.session.query(Channels).join(Channels.roles).filter(Channels.uuid == channel_id).first()
        return self._object_has_role_for_user(channel, the_role, user_id)

    @with_session
    def _remove_role_on_room_for_user(self, the_role: str, room_id: str, user_id: str) -> None:
        room = self.session.query(Rooms).outerjoin(Rooms.roles).filter(Rooms.uuid == room_id).first()
        if room is None:
            raise NoSuchRoomException(room_id)

        for role in room.roles:
            if role.user_id == user_id and the_role in role.roles:
                roles = set(role.roles.split(','))
                roles.remove(the_role)
                role.roles = ','.join(roles)
                self.session.commit()
                return

    @with_session
    def _remove_role_on_channel_for_user(self, the_role: str, channel_id: str, user_id: str) -> None:
        channel = self.session.query(Channels).outerjoin(Channels.roles).filter(Channels.uuid == channel_id).first()
        if channel is None:
            raise NoSuchChannelException(channel_id)

        for role in channel.roles:
            if role.user_id == user_id and the_role in role.roles:
                roles = set(role.roles.split(','))
                roles.remove(the_role)
                role.roles = ','.join(roles)
                self.session.commit()
                return

    @with_session
    def _set_role_on_room_for_user(self, the_role: Rooms, room_id: str, user_id: str):
        room = self.session.query(Rooms).outerjoin(Rooms.roles).filter(Rooms.uuid == room_id).first()
        if room is None:
            raise NoSuchRoomException(room_id)

        found_role = None
        for role in room.roles:
            if role.user_id == user_id:
                found_role = role
                if the_role in role.roles:
                    return

        if found_role is None:
            found_role = RoomRoles()
            found_role.user_id = user_id
            found_role.room = room
            found_role.roles = the_role
        else:
            roles = set(found_role.roles.split(','))
            roles.add(the_role)
            found_role.roles = ','.join(roles)

        self.session.add(found_role)
        self.session.commit()

    @with_session
    def _set_role_on_channel_for_user(self, the_role: str, channel_id: str, user_id: str) -> None:
        channel = self.session.query(Channels).outerjoin(Channels.roles).filter(Channels.uuid == channel_id).first()
        if channel is None:
            raise NoSuchChannelException(channel_id)

        found_role = None
        for role in channel.roles:
            if role.user_id == user_id:
                found_role = role
                if the_role in role.roles:
                    return

        if found_role is None:
            found_role = ChannelRoles()
            found_role.user_id = user_id
            found_role.channel = channel
            found_role.roles = the_role
        else:
            roles = set(found_role.roles.split(','))
            roles.add(the_role)
            found_role.roles = ','.join(roles)

        self.session.add(found_role)
        self.session.commit()

    def set_super_user(self, user_id: str) -> None:
        self._add_global_role(user_id, RoleKeys.SUPER_USER)

    def remove_super_user(self, user_id: str) -> None:
        self._remove_global_role(user_id, RoleKeys.SUPER_USER)

    def is_super_user(self, user_id: str) -> bool:
        self._has_global_role(user_id, RoleKeys.SUPER_USER)

    def is_moderator(self, room_id: str, user_id: str) -> bool:
        return self._room_has_role_for_user(RoleKeys.MODERATOR, room_id, user_id)

    def is_admin(self, channel_id: str, user_id: str) -> bool:
        return self._channel_has_role_for_user(RoleKeys.ADMIN, channel_id, user_id)

    def is_owner(self, room_id: str, user_id: str) -> bool:
        return self._room_has_role_for_user(RoleKeys.OWNER, room_id, user_id)

    def is_owner_channel(self, channel_id: str, user_id: str) -> bool:
        return self._channel_has_role_for_user(RoleKeys.OWNER, channel_id, user_id)

    def set_admin(self, channel_id: str, user_id: str) -> None:
        if not self.channel_exists(channel_id):
            raise NoSuchChannelException(channel_id)
        self._set_role_on_channel_for_user(RoleKeys.ADMIN, channel_id, user_id)

    def set_moderator(self, room_id: str, user_id: str) -> None:
        if self.channel_for_room(room_id) is None:
            raise NoSuchRoomException(room_id)
        self._set_role_on_room_for_user(RoleKeys.MODERATOR, room_id, user_id)

    def set_owner(self, room_id: str, user_id: str) -> None:
        if self.channel_for_room(room_id) is None:
            raise NoSuchRoomException(room_id)
        self._set_role_on_room_for_user(RoleKeys.OWNER, room_id, user_id)

    def set_owner_channel(self, channel_id: str, user_id: str) -> None:
        if not self.channel_exists(channel_id):
            raise NoSuchChannelException(channel_id)
        self._set_role_on_channel_for_user(RoleKeys.OWNER, channel_id, user_id)

    def remove_admin(self, channel_id: str, user_id: str) -> None:
        if not self.channel_exists(channel_id):
            raise NoSuchChannelException(channel_id)
        self._remove_role_on_channel_for_user(RoleKeys.ADMIN, channel_id, user_id)

    def remove_owner_channel(self, channel_id: str, user_id: str) -> None:
        if not self.channel_exists(channel_id):
            raise NoSuchChannelException(channel_id)
        self._remove_role_on_channel_for_user(RoleKeys.OWNER, channel_id, user_id)

    def remove_moderator(self, room_id: str, user_id: str) -> None:
        if self.channel_for_room(room_id) is None:
            raise NoSuchRoomException(room_id)
        self._remove_role_on_room_for_user(RoleKeys.MODERATOR, room_id, user_id)

    def remove_owner(self, room_id: str, user_id: str) -> None:
        if self.channel_for_room(room_id) is None:
            raise NoSuchRoomException(room_id)
        self._remove_role_on_room_for_user(RoleKeys.OWNER, room_id, user_id)

    @with_session
    def delete_acl_in_room_for_action(self, room_id: str, acl_type: str, action: str) -> None:
        room = self.session.query(Rooms).filter(Rooms.uuid == room_id).first()
        if room is None:
            raise NoSuchRoomException(room_id)

        if action not in ApiActions.all_api_actions:
            raise InvalidApiActionException(action)

        found_acl = self.session.query(Acls)\
            .join(Acls.room)\
            .filter(Acls.acl_type == acl_type)\
            .filter(Rooms.uuid == room_id).first()

        if found_acl is None:
            return

        self.session.delete(found_acl)
        self.session.commit()

    @with_session
    def delete_acl_in_channel_for_action(self, channel_id: str, acl_type: str, action: str) -> None:
        channel = self.session.query(Channels).filter(Channels.uuid == channel_id).first()
        if channel is None:
            raise NoSuchChannelException(channel_id)

        if action not in ApiActions.all_api_actions:
            raise InvalidApiActionException(action)

        found_acl = self.session.query(Acls).join(Acls.channel).filter(Channels.uuid == channel_id).first()
        if found_acl is None:
            return

        found_acl.__setattr__(acl_type, None)
        self.session.commit()

    def add_acls_in_room_for_action(self, room_id: str, action: str, new_acls: dict) -> None:
        @with_session
        def _add_acls_in_room_for_action(self):
            room = self.session.query(Rooms)\
                .outerjoin(Rooms.acls)\
                .filter(Rooms.uuid == room_id)\
                .first()

            if room is None:
                raise NoSuchRoomException(room_id)
            existing_acls = room.acls
            to_delete, to_add = self._add_acls(existing_acls, new_acls, action, ApiTargets.ROOM)

            for acl in to_delete:
                self.session.delete(acl)
            for acl in to_add:
                acl.room = room
                self.session.add(acl)

            self.session.commit()

        if new_acls is None or len(new_acls) == 0:
            return
        _add_acls_in_room_for_action(self)

    def add_acls_in_channel_for_action(self, channel_id: str, action: str, new_acls: dict) -> None:
        @with_session
        def _add_acls_in_channel_for_action(self):
            channel = self.session.query(Channels)\
                .outerjoin(Channels.acls)\
                .filter(Channels.uuid == channel_id)\
                .first()

            if channel is None:
                raise NoSuchChannelException(channel_id)
            existing_acls = channel.acls
            to_delete, to_add = self._add_acls(existing_acls, new_acls, action, ApiTargets.CHANNEL)

            for acl in to_delete:
                self.session.delete(acl)
            for acl in to_add:
                acl.channel = channel
                self.session.add(acl)

            self.session.commit()

        if new_acls is None or len(new_acls) == 0:
            return
        _add_acls_in_channel_for_action(self)

    def _add_acls(self, existing_acls: list, new_acls: dict, action: str, target: str) -> (list, list):
        updated_acls = set()
        to_delete = list()
        if existing_acls is not None and len(existing_acls) > 0:
            for acl in existing_acls:
                if acl.action != action:
                    continue
                if acl.acl_type not in new_acls.keys():
                    continue

                new_value = new_acls[acl.acl_type]
                if new_value is None or len(new_value.strip()) == 0:
                    to_delete.append(acl)
                else:
                    acl.acl_value = new_value
                updated_acls.add(acl.acl_type)

        to_add = list()
        for acl_type, acl_value in new_acls.items():
            # already deleted/updated
            if acl_type in updated_acls:
                continue

            if acl_type not in self._get_acls_for_target_and_action(target, action):
                raise InvalidAclTypeException(acl_type)

            if not self._validate_acl_for_target_and_action(target, action, acl_type, acl_value):
                raise InvalidAclValueException(acl_type, acl_value)

            acl = Acls()
            acl.action = action
            acl.acl_type = acl_type
            acl.acl_value = acl_value
            to_add.append(acl)

        return to_delete, to_add

    def _validate_acl_for_target_and_action(self, target: str, action: str, acl_type: str, acl_value: str):
        validators = self._get_acls_for_target('validation')
        try:
            validators[acl_type]['value'].validate_new_acl(acl_value)
        except ValidationException as e:
            logger.info('new acl values "%s" did not validate for type "%s": %s' % (acl_value, acl_type, str(e)))
            return False
        return True

    def _get_acls(self) -> dict:
        return self.env.config.get(ConfigKeys.ACL)

    def _get_acls_for_target(self, target: str) -> dict:
        return self._get_acls().get(target)

    def _get_acls_for_target_and_action(self, target, action) -> list:
        acls_for_target = self._get_acls_for_target(target)
        if acls_for_target is None:
            return list()

        acls_for_action = acls_for_target.get(action)
        if acls_for_action is None:
            return list()

        acls = acls_for_action.get('acls')
        if acls is None:
            return list()
        return acls

    def update_acl_in_room_for_action(self, channel_id: str, room_id: str, action: str, acl_type: str, acl_value: str) -> None:
        self.add_acls(room_id, {acl_type: acl_value})

    def update_acl_in_channel_for_action(self, channel_id: str, room_id: str, action: str, acl_type: str, acl_value: str) -> None:
        self.add_acls_channel(channel_id, {acl_type: acl_value})

    @with_session
    def get_acl_validation_value(self, acl_type: str, validation_method) -> str:
        acl_config = self.session.query(AclConfigs)\
            .filter(AclConfigs.acl_type == acl_type)\
            .filter(AclConfigs.method == validation_method)\
            .first()

        if acl_config is None or acl_config.acl_value is None or len(acl_config.acl_value.strip()) == 0:
            raise AclValueNotFoundException(acl_type, validation_method)
        return acl_config.acl_value

    def get_all_acls_channel(self, channel_id: str) -> dict:
        # TODO: cache
        channel = self.session.query(Channels)\
            .outerjoin(Channels.acls)\
            .filter(Channels.uuid == channel_id)\
            .first()

        if channel is None:
            raise NoSuchChannelException(channel_id)

        found_acls = channel.acls
        if found_acls is None or len(found_acls) == 0:
            return dict()

        acls = dict()
        for acl in found_acls:
            if acl.action not in acls:
                acls[acl.action] = dict()
            acls[acl.acl_type] = acl.acl_value
        return acls

    def get_all_acls_room(self, room_id: str) -> dict:
        # TODO: cache
        room = self.session.query(Rooms)\
            .outerjoin(Rooms.acls)\
            .filter(Rooms.uuid == room_id)\
            .first()

        if room is None:
            raise NoSuchRoomException(room_id)

        found_acls = room.acls
        if found_acls is None or len(found_acls) == 0:
            return dict()

        acls = dict()
        for acl in found_acls:
            if acl.action not in acls:
                acls[acl.action] = dict()
            acls[acl.acl_action][acl.acl_type] = acl.acl_value
        return acls

    @with_session
    def get_acls_in_room_for_action(self, room_id: str, action: str):
        # TODO: cache
        room = self.session.query(Rooms)\
            .outerjoin(Rooms.acls)\
            .filter(Rooms.uuid == room_id)\
            .first()

        if room is None:
            raise NoSuchRoomException(room_id)

        found_acls = room.acls
        if found_acls is None or len(found_acls) == 0:
            return dict()

        acls = dict()
        for found_acl in found_acls:
            if found_acl.action != action:
                continue
            acls[found_acl.acl_type] = found_acl.acl_value
        return acls

    @with_session
    def get_acls_in_channel_for_action(self, channel_id: str, action: str):
        # TODO: cache
        channel = self.session.query(Channels)\
            .outerjoin(Channels.acls)\
            .filter(Channels.uuid == channel_id)\
            .first()

        if channel is None:
            raise NoSuchChannelException(channel_id)

        found_acls = channel.acls
        if found_acls is None or len(found_acls) == 0:
            return dict()

        acls = dict()
        for found_acl in found_acls:
            if found_acl.action != action:
                continue
            acls[found_acl.acl_type] = found_acl.acl_value
        return acls

    @with_session
    def update_last_read_for(self, users: str, room_id: str, time_stamp: int) -> None:
        for user_id in users:
            last_read = self.session.query(LastReads)\
                .filter(LastReads.user_uuid == user_id)\
                .filter(LastReads.room_uuid == room_id)

            if last_read is None:
                last_read = LastReads()
                last_read.room_uuid = room_id
                last_read.user_uuid = user_id

            last_read.time_stamp = time_stamp
            self.session.add(last_read)
        self.session.commit()

    @with_session
    def get_last_read_timestamp(self, room_id: str, user_id: str) -> int:
        last_read = self.session.query(LastReads)\
            .filter(LastReads.user_id == user_id)\
            .filter(LastReads.room_uuid == room_id)\
            .first()

        if last_read is None:
            return None

        return last_read.time_stamp

    @with_session
    def set_user_name(self, user_id: str, user_name: str):
        user = self.session.query(Users).filter(Users.uuid == user_id).first()
        if user is None:
            user = Users()
            user.uuid = user_id
        user.name = user_name
        self.session.add(user)
        self.session.commit()

    def create_user(self, user_id: str, user_name: str) -> None:
        @with_session
        def _create_user(self):
            user = Users()
            user.uuid = user_id
            user.name = user_name
            self.session.add(user)
            self.session.commit()

        try:
            self.get_user_name(user_id)
            raise UserExistsException(user_id)
        except NoSuchUserException:
            pass

        return _create_user(self)

    @with_session
    def get_super_users(self) -> dict:
        roles = self.session.query(GlobalRoles)\
            .filter(GlobalRoles.roles.like('%{}%'.format(RoleKeys.SUPER_USER)))\
            .all()

        if roles is None or len(roles) == 0:
            return dict()

        users = dict()
        for role in roles:
            users[role.user_id] = self.get_user_name(role.user_id)
        return users

    def get_user_name(self, user_id: str) -> str:
        @with_session
        def _get_user_name(self):
            user = self.session.query(Users).filter(Users.uuid == user_id).first()
            if user is None:
                raise NoSuchUserException(user_id)
            return user.name

        user_name = self.env.cache.get_user_name(user_id)
        if user_name is not None:
            return user_name

        user_name = _get_user_name(self)
        self.env.cache.set_user_name(user_id, user_name)
        return user_name

    def _get_users_with_role(self, roles, role_key):
        if roles is None or len(roles) == 0:
            return dict()

        found = dict()
        for role in roles:
            if role_key not in role.roles.split(','):
                continue

            try:
                found[role.user_id] = self.get_user_name(role.user_id)
            except NoSuchUserException:
                logger.error('no username found for user_id %s' % role.user_id)
        return found

    @with_session
    def _get_users_with_role_in_channel(self, channel_id: str, role_key: str) -> dict:
        roles = self.session.query(ChannelRoles).join(ChannelRoles.channel).filter(Channels.uuid == channel_id).all()
        return self._get_users_with_role(roles, role_key)

    @with_session
    def _get_users_with_role_in_room(self, room_id: str, role_key: str) -> dict:
        roles = self.session.query(RoomRoles).join(RoomRoles.room).filter(Rooms.uuid == room_id).all()
        return self._get_users_with_role(roles, role_key)

    def get_owners_channel(self, channel_id: str) -> dict:
        return self._get_users_with_role_in_channel(channel_id, RoleKeys.OWNER)

    def get_admins_channel(self, channel_id: str) -> dict:
        return self._get_users_with_role_in_channel(channel_id, RoleKeys.ADMIN)

    def get_owners_room(self, room_id: str) -> dict:
        return self._get_users_with_role_in_room(room_id, RoleKeys.OWNER)

    def get_moderators_room(self, room_id: str) -> dict:
        return self._get_users_with_role_in_room(room_id, RoleKeys.MODERATOR)

    def get_room_name(self, room_id: str) -> str:
        @with_session
        def _get_room_name(self):
            room = self.session.query(Rooms).filter(Rooms.uuid == room_id).first()
            if room is None:
                raise NoSuchRoomException(room_id)
            return room.name

        value = self.env.cache.get_room_name(room_id)
        if value is not None:
            return value
        return _get_room_name(self)

    def get_channel_name(self, channel_id: str) -> str:
        @with_session
        def _get_channel_name(self):
            channel = self.session.query(Channels).filter(Channels.uuid == channel_id).first()
            if channel is None:
                raise NoSuchChannelException(channel_id)
            return channel.name

        value = self.env.cache.get_channel_name(channel_id)
        if value is not None:
            return value
        return _get_channel_name(self)

    def _get_banned_users(self, all_bans):
        output = dict()
        if all_bans is None or len(all_bans) == 0:
            return output

        should_commit = False
        now = datetime.utcnow()

        for ban in all_bans:
            if now > ban.timestamp:
                self.session.delete(ban)
                should_commit = True
                continue

            output[ban.user_id] = {
                'name': ban.user_name,
                'duration': ban.duration,
                'timestamp': ban.timestamp.strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
            }

        if should_commit:
            self.session.commit()
        return output

    def is_banned_globally(self, user_id: str) -> (bool, Union[str, None]):
        now = datetime.utcnow()
        duration, time, username = self.env.cache.get_global_ban_timestamp(user_id)
        if time is not None:
            if time == '':
                return False, None

            time = datetime.fromtimestamp(time)
            if now > time:
                self.remove_global_ban(user_id)
                return False, None
            return True, str((time-now).seconds)

        duration, time, username = self.get_global_ban_timestamp(user_id)
        if time is None:
            self.env.cache.set_global_ban_timestamp(user_id, '', '', '')
            return False, None
        if now > time:
            self.remove_global_ban(user_id)
            return False, None

        self.env.cache.set_global_ban_timestamp(user_id, time.strftime(ConfigKeys.DEFAULT_DATE_FORMAT))
        return True, str((time-now).seconds)

    def is_banned_from_channel(self, channel_id: str, user_id: str) -> (bool, Union[str, None]):
        now = datetime.utcnow()
        duration, time, username = self.env.cache.get_channel_ban_timestamp(channel_id, user_id)
        if time is not None:
            if time == '':
                return False, None

            time = datetime.fromtimestamp(time)
            if now > time:
                self.remove_channel_ban(channel_id, user_id)
                return False, None
            return True, str((time-now).seconds)

        duration, time, username = self.get_channel_ban_timestamp(channel_id, user_id)
        if time is None:
            self.env.cache.set_channel_ban_timestamp(channel_id, user_id, '', '', '')
            return False, None
        if now > time:
            self.remove_channel_ban(channel_id, user_id)
            return False, None

        self.env.cache.set_channel_ban_timestamp(channel_id, user_id, time.strftime(ConfigKeys.DEFAULT_DATE_FORMAT))
        return True, str((time-now).seconds)

    def is_banned_from_room(self, room_id: str, user_id: str) -> (bool, Union[str, None]):
        now = datetime.utcnow()
        duration, time, username = self.env.cache.get_room_ban_timestamp(room_id, user_id)
        if time is not None:
            if time == '':
                return False, None

            time = datetime.fromtimestamp(time)
            if now > time:
                self.remove_room_ban(room_id, user_id)
                return False, None
            return True, str((time-now).seconds)

        duration, time, username = self.get_room_ban_timestamp(room_id, user_id)
        if time is None:
            self.env.cache.set_room_ban_timestamp(room_id, user_id, '', '', '')
            return False, None
        if now > time:
            self.remove_room_ban(room_id, user_id)
            return False, None

        self.env.cache.set_room_ban_timestamp(room_id, user_id, time.strftime(ConfigKeys.DEFAULT_DATE_FORMAT))
        return True, str((time-now).seconds)

    @with_session
    def get_global_ban_timestamp(self, user_id: str) -> (str, str, str):
        global_ban = self.session.query(Bans)\
            .filter(Bans.is_global.is_(True))\
            .filter(Bans.user_id == user_id)\
            .first()

        if global_ban is not None:
            return global_ban.duration, global_ban.timestamp, global_ban.user_name
        return None, None, None

    @with_session
    def get_channel_ban_timestamp(self, channel_id: str, user_id: str) -> (str, str, str):
        channel_ban = self.session.query(Bans)\
            .join(Bans.channel)\
            .filter(Bans.is_global.is_(False))\
            .filter(Channels.uuid == channel_id)\
            .filter(Bans.user_id == user_id)\
            .first()

        if channel_ban is not None:
            return channel_ban.duration, channel_ban.timestamp, channel_ban.use_rname
        return None, None, None

    @with_session
    def get_room_ban_timestamp(self, room_id: str, user_id: str) -> (str, str, str):
        room_ban = self.session.query(Bans)\
            .join(Bans.room)\
            .filter(Bans.is_global.is_(False))\
            .filter(Rooms.uuid == room_id)\
            .filter(Bans.user_id == user_id)\
            .first()

        if room_ban is not None:
            return room_ban.duration, room_ban.timestamp, room_ban.use_rname
        return None, None, None

    def get_user_ban_status(self, room_id: str, user_id: str) -> dict:
        """
        TODO: fix this method, it's a horribly ugly friday night hack
        """
        def _has_passed(the_time):
            now = datetime.utcnow()
            return now > datetime.fromtimestamp(int(the_time))

        def _set_in_cache_if_none(_gtime, _ctime, _rtime):
            if _gtime is None:
                duration, _gtime, username = self.get_global_ban_timestamp(user_id)
                if _gtime is None:
                    duration, _gtime, username = '', '', ''
                else:
                    _gtime = _gtime.timestamp()
                self.env.cache.set_global_ban_timestamp(user_id, duration, _gtime, username)
            if _ctime is None:
                duration, _ctime, username = self.get_channel_ban_timestamp(channel_id, user_id)
                if _ctime is None:
                    duration, _ctime, username = '', '', ''
                else:
                    _ctime = _ctime.timestamp()
                self.env.cache.set_channel_ban_timestamp(channel_id, user_id, duration, _ctime, username)
            if _rtime is None:
                duration, _rtime, username = self.get_room_ban_timestamp(room_id, user_id)
                if _rtime is None:
                    _rtime = ''
                else:
                    _rtime = _rtime.timestamp()
                self.env.cache.set_room_ban_timestamp(room_id, user_id, duration, _rtime, username)
            return _gtime, _ctime, _rtime

        def _update_if_passed(_gtime, _ctime, _rtime):
            if _gtime is not None and _gtime != '':
                if _has_passed(_gtime):
                    self.remove_global_ban(user_id)
                    _gtime = ''
            if _ctime is not None and _ctime != '':
                if _has_passed(_ctime):
                    self.remove_channel_ban(channel_id, user_id)
                    _ctime = ''
            if _rtime is not None and _rtime != '':
                if _has_passed(_rtime):
                    self.remove_room_ban(room_id, user_id)
                    _rtime = ''
            return _gtime or '', _ctime or '', _rtime or ''

        channel_id = self.channel_for_room(room_id)
        _, gtime, _ = self.env.cache.get_global_ban_timestamp(user_id)
        _, ctime, _ = self.env.cache.get_channel_ban_timestamp(channel_id, user_id)
        _, rtime, _ = self.env.cache.get_room_ban_timestamp(room_id, user_id)

        # even if no ban, set in cache so we don't have to check db
        gtime, ctime, rtime = _set_in_cache_if_none(gtime, ctime, rtime)

        # empty string means there is no ban
        gtime, ctime, rtime = _update_if_passed(gtime, ctime, rtime)

        return {
            'global': gtime,
            'channel': ctime,
            'room': rtime
        }

    @with_session
    def remove_global_ban(self, user_id):
        self.env.cache.set_global_ban_timestamp(user_id, '', '', '')
        ban = self.session.query(Bans)\
            .filter(Bans.user_id == user_id)\
            .filter(Bans.is_global.is_(True)).first()
        if ban is None:
            return
        self.session.delete(ban)

    @with_session
    def remove_channel_ban(self, channel_id, user_id):
        self.env.cache.set_channel_ban_timestamp(channel_id, user_id, '', '', '')
        ban = self.session.query(Bans)\
            .join(Bans.channel)\
            .filter(Channels.uuid == channel_id)\
            .filter(Bans.user_id == user_id)\
            .filter(Bans.is_global.is_(False)).first()
        if ban is None:
            return
        self.session.delete(ban)

    @with_session
    def remove_room_ban(self, room_id, user_id):
        self.env.cache.set_room_ban_timestamp(room_id, user_id, '', '', '')
        ban = self.session.query(Bans)\
            .join(Bans.room)\
            .filter(Rooms.uuid == room_id)\
            .filter(Bans.user_id == user_id)\
            .filter(Bans.is_global.is_(False)).first()
        if ban is None:
            return
        self.session.delete(ban)

    @with_session
    def get_banned_users_global(self, room_id: str) -> dict:
        all_bans = self.session.query(Bans).filter(Bans.is_global.is_(True)).all()
        return self._get_banned_users(all_bans)

    @with_session
    def get_banned_users_for_channel(self, channel_id: str) -> dict:
        all_bans = self.session.query(Bans).join(Bans.channel).filter(Channels.uuid == channel_id).all()
        return self._get_banned_users(all_bans)

    @with_session
    def get_banned_users_for_room(self, room_id: str) -> dict:
        all_bans = self.session.query(Bans).join(Bans.room).filter(Rooms.uuid == room_id).all()
        return self._get_banned_users(all_bans)

    def get_banned_users(self):
        @with_session
        def _get_the_bans(_self):
            output = {
                'global': dict(),
                'channels': dict(),
                'rooms': dict()
            }

            all_bans = _self.session.query(Bans).outerjoin(Bans.room).outerjoin(Bans.channel).all()
            if all_bans is None or len(all_bans) == 0:
                return output

            should_commit = False
            now = datetime.utcnow()

            for ban in all_bans:
                if now > ban.timestamp:
                    _self.session.delete(ban)
                    should_commit = True
                    continue

                if ban.room is not None:
                    if ban.room.uuid not in output['rooms']:
                        output['rooms'][ban.room.uuid] = dict()
                        output['rooms'][ban.room.uuid]['users'] = dict()

                    output['rooms'][ban.room.uuid]['users'][ban.user_id] = {
                        'name': ban.user_name,
                        'duration': ban.duration,
                        'timestamp': ban.timestamp.strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
                    }
                elif ban.channel is not None:
                    if ban.channel.uuid not in output['channels']:
                        output['channels'][ban.channel.uuid] = dict()
                        output['channels'][ban.channel.uuid]['users'] = dict()

                    output['channels'][ban.channel.uuid]['users'][ban.user_id] = {
                        'name': ban.user_name,
                        'duration': ban.duration,
                        'timestamp': ban.timestamp.strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
                    }
                elif ban.is_global:
                    output['global'][ban.user_id] = {
                        'name': ban.user_name,
                        'duration': ban.duration,
                        'timestamp': ban.timestamp.strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
                    }

            if should_commit:
                _self.session.commit()
            return output

        def _add_names_to_rooms_and_channels(output):
            for room_id in output['rooms'].keys():
                output['rooms'][room_id]['name'] = self.get_room_name(room_id)

            for channel_id in output['channels'].keys():
                output['channels'][channel_id]['name'] = self.get_channel_name(channel_id)
            return output

        return _add_names_to_rooms_and_channels(_get_the_bans(self))

    @with_session
    def kick_user(self, room_id: str, user_id: str) -> None:
        self.leave_room(user_id, room_id)

    def _remove_user_from_room(self, session, room_id: str, user_id: str) -> None:
        room = self.session.query(Rooms)\
            .join(Rooms.users)\
            .filter(Rooms.uuid == room_id)\
            .filter(Users.uuid == user_id)\
            .first()

        if room is not None:
            room.users.remove(room.users[0])
            self.session.add(room)

    def _remove_user_from_rooms_in_channel(self, session, channel_id: str, user_id: str) -> None:
        channel = self.session.query(Channels)\
            .join(Channels.rooms)\
            .join(Rooms.users)\
            .filter(Channels.uuid == channel_id)\
            .filter(Users.uuid == user_id)\
            .first()

        if channel is not None:
            if channel.rooms is not None and len(channel.rooms) > 0:
                for room in channel.rooms:
                    if room.users is not None and len(room.users) > 0:
                        for user in room.users:
                            if user.uuid == user_id:
                                room.users.remove(user)
                    self.session.add(room)

    @with_session
    def ban_user_global(self, user_id: str, ban_timestamp: str, ban_duration: str):
        ban = self.session.query(Bans)\
            .filter(Bans.user_id == user_id)\
            .filter(Bans.is_global.is_(True)).first()

        username = ''
        try:
            username = self.get_user_name(user_id)
        except NoSuchUserException:
            pass

        self.remove_current_rooms_for_user(user_id)
        self.env.cache.set_global_ban_timestamp(
                user_id, ban_duration, ban_timestamp, self.get_user_name(user_id))

        if ban is None:
            ban = Bans()
            ban.uuid = str(uuid())
            ban.user_id = user_id
            ban.user_name = username
            ban.is_global = True

        ban.timestamp = datetime.fromtimestamp(int(ban_timestamp))
        ban.duration = ban_duration

        self.session.add(ban)
        self.session.commit()

    @with_session
    def ban_user_room(self, user_id: str, ban_timestamp: str, ban_duration: str, room_id: str):
        try:
            self.channel_for_room(room_id)
        except NoChannelFoundException:
            raise NoSuchRoomException(room_id)

        username = ''
        try:
            username = self.get_user_name(user_id)
        except NoSuchUserException:
            pass

        self._remove_user_from_room(self.session, room_id, user_id)
        self.env.cache.set_room_ban_timestamp(
                room_id, user_id, ban_duration, ban_timestamp, self.get_user_name(user_id))

        ban = self.session.query(Bans)\
            .join(Bans.room)\
            .filter(Bans.user_id == user_id)\
            .filter(Rooms.uuid == room_id).first()

        if ban is None:
            room = self.session.query(Rooms).filter(Rooms.uuid == room_id).first()
            ban = Bans()
            ban.uuid = str(uuid())
            ban.user_id = user_id
            ban.room = room
            ban.user_name = username

        ban.timestamp = datetime.fromtimestamp(int(ban_timestamp))
        ban.duration = ban_duration

        self.session.add(ban)
        self.session.commit()

    @with_session
    def ban_user_channel(self, user_id: str, ban_timestamp: str, ban_duration: str, channel_id: str):
        if not self.channel_exists(channel_id):
            raise NoSuchChannelException(channel_id)

        username = ''
        try:
            username = self.get_user_name(user_id)
        except NoSuchUserException:
            pass

        self._remove_user_from_rooms_in_channel(self.session, channel_id, user_id)
        self.env.cache.set_channel_ban_timestamp(
                channel_id, user_id, ban_duration, ban_timestamp, self.get_user_name(user_id))

        ban = self.session.query(Bans)\
            .join(Bans.channel)\
            .filter(Bans.user_id == user_id)\
            .filter(Channels.uuid == channel_id).first()

        if ban is None:
            channel = self.session.query(Channels).filter(Channels.uuid == channel_id).first()
            ban = Bans()
            ban.uuid = str(uuid())
            ban.user_id = user_id
            ban.channel = channel
            ban.user_name = username

        ban.timestamp = datetime.fromtimestamp(int(ban_timestamp))
        ban.duration = ban_duration

        self.session.add(ban)
        self.session.commit()
