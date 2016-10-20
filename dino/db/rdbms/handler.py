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

from dino.config import ConfigKeys
from dino.config import RoleKeys
from dino.config import UserKeys
from dino.config import SessionKeys
from dino.db import IDatabase
from dino.db.rdbms.dbman import Database
from dino.db.rdbms.mock import MockDatabase
from dino.db.rdbms.models import ChannelRoles
from dino.db.rdbms.models import Channels
from dino.db.rdbms.models import RoomRoles
from dino.db.rdbms.models import Rooms
from dino.db.rdbms.models import Acls
from dino.db.rdbms.models import UserStatus
from dino.db.rdbms.models import Users
from dino.db.rdbms.models import LastReads
from dino.validator import Validator

from dino.exceptions import ChannelExistsException
from dino.exceptions import NoSuchChannelException
from dino.exceptions import NoSuchRoomException
from dino.exceptions import RoomExistsException
from dino.exceptions import RoomNameExistsForChannelException
from dino.exceptions import NoChannelFoundException
from dino.exceptions import InvalidAclTypeException
from dino.exceptions import InvalidAclValueException

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

    @with_session
    def remove_current_rooms_for_user(self, user_id: str) -> None:
        rows = self.session.query(Users).filter(Users.uuid == user_id).all()
        if len(rows) == 0:
            return

        for row in rows:
            self.session.delete(row)
        self.session.commit()

    @with_session
    def get_channels(self) -> dict:
        rows = self.session.query(Channels).all()
        channels = dict()
        for row in rows:
            channels[row.uuid] = row.name
        return channels

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

        if self.channel_exists(channel_id):
            raise ChannelExistsException(channel_id)
        _create_channel(self)

    @with_session
    def create_room(self, room_name: str, room_id: str, channel_id: str, user_id: str, user_name: str) -> None:
        if self.room_exists(channel_id, room_id):
            raise RoomExistsException(room_id)

        if self.room_name_exists(channel_id, room_name):
            raise RoomNameExistsForChannelException(channel_id, room_name)

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

        room = user.rooms[0]
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

    def _room_has_role_for_user(self, the_role: str, room_id: str, user_id: str) -> bool:
        # TODO: cache
        room = self.session.query(Rooms).join(Rooms.roles).filter(Rooms.uuid == room_id).first()
        return self._object_has_role_for_user(room, the_role, user_id)

    def _channel_has_role_for_user(self, the_role: str, channel_id: str, user_id: str) -> bool:
        # TODO: cache
        channel = self.session.query(Channels).join(Channels.roles).filter(Channels.uuid == channel_id).first()
        return self._object_has_role_for_user(channel, the_role, user_id)

    @with_session
    def _set_role_on_room_for_user(self, the_role: Rooms, room_id: str, user_id: str):
        room = self.session.query(Rooms).join(Rooms.roles).filter(Rooms.uuid == room_id).first()
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
    def _set_role_on_channel_for_user(self, the_role: Channels, channel_id: str, user_id: str):
        channel = self.session.query(Channels).join(Channels.roles).filter(Channels.uuid == channel_id).first()
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

    @with_session
    def is_moderator(self, room_id: str, user_id: str) -> bool:
        return self._room_has_role_for_user(RoleKeys.MODERATOR, room_id, user_id)

    @with_session
    def is_admin(self, channel_id: str, user_id: str) -> bool:
        return self._channel_has_role_for_user(RoleKeys.ADMIN, channel_id, user_id)

    @with_session
    def is_owner(self, room_id: str, user_id: str) -> bool:
        return self._room_has_role_for_user(RoleKeys.OWNER, room_id, user_id)

    @with_session
    def is_owner_channel(self, channel_id: str, user_id: str) -> bool:
        return self._channel_has_role_for_user(RoleKeys.OWNER, channel_id, user_id)

    @with_session
    def set_admin(self, channel_id: str, user_id: str) -> None:
        if not self.channel_exists(channel_id):
            raise NoSuchChannelException(channel_id)
        self._set_role_on_channel_for_user(RoleKeys.ADMIN, channel_id, user_id)

    @with_session
    def set_moderator(self, room_id: str, user_id: str) -> None:
        if self.channel_for_room(room_id) is None:
            raise NoSuchRoomException(room_id)
        self._set_role_on_room_for_user(RoleKeys.MODERATOR, room_id, user_id)

    @with_session
    def set_owner(self, room_id: str, user_id: str) -> None:
        if self.channel_for_room(room_id) is None:
            raise NoSuchRoomException(room_id)
        self._set_role_on_room_for_user(RoleKeys.OWNER, room_id, user_id)

    @with_session
    def set_owner_channel(self, channel_id: str, user_id: str) -> None:
        if not self.channel_exists(channel_id):
            raise NoSuchChannelException(channel_id)
        self._set_role_on_channel_for_user(RoleKeys.OWNER, channel_id, user_id)

    @with_session
    def room_allows_cross_group_messaging(self, room_uuid: str) -> bool:
        acls = self.get_acls(room_uuid)
        if SessionKeys.crossgroup.value not in acls:
            return False
        return acls[SessionKeys.crossgroup.value] == 'y'

    @with_session
    def delete_acl(self, room_id: str, acl_type: str) -> None:
        room = self.session.query(Rooms).filter(Rooms.uuid == room_id).first()
        if room is None:
            raise NoSuchRoomException(room_id)

        found_acl = self.session.query(Acls).join(Acls.room).filter(Rooms.uuid == room_id).first()
        if found_acl is None:
            return

        found_acl.__setattr__(acl_type, None)
        self.session.commit()

    @with_session
    def add_acls(self, room_id: str, acls: dict) -> None:
        if acls is None or len(acls) == 0:
            return

        room = self.session.query(Rooms).filter(Rooms.uuid == room_id).first()
        if room is None:
            raise NoSuchRoomException(room_id)

        acl = self.session.query(Acls).join(Acls.room).filter(Rooms.uuid == room_id).first()
        if acl is None:
            acl = Acls()

        for acl_type, acl_value in acls.items():
            if acl_type not in Validator.ACL_VALIDATORS:
                raise InvalidAclTypeException(acl_type)

            if not Validator.ACL_VALIDATORS[acl_type](acl_value):
                raise InvalidAclValueException(acl_type, acl_value)

            acl.__setattr__(acl_type, acl_value)

        room.acl = acl
        self.session.commit()

    @with_session
    def get_acls(self, room_id: str) -> list:
        room = self.session.query(Rooms).outerjoin(Rooms.acl).filter(Rooms.uuid == room_id).first()
        if room is None:
            raise NoSuchRoomException(room_id)

        found_acl = room.acl
        if found_acl is None:
            return dict()

        acls = dict()
        for key in Validator.ACL_VALIDATORS.keys():
            if key not in found_acl.__dict__:
                continue

            value = found_acl.__getattribute__(key)
            if value is not None:
                acls[key] = value

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
            .filter(LastReads.user_uuid == user_id)\
            .filter(LastReads.room_uuid == room_id)\
            .first()

        if last_read is None:
            return None

        return last_read.time_stamp
