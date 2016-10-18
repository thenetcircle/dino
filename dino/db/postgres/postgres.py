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

from functools import wraps
from zope.interface import implementer

from dino.config import ConfigKeys
from dino.config import RoleKeys
from dino.db import IDatabase
from dino.db.postgres.dbman import Database
from dino.db.postgres.mock import MockDatabase
from dino.db.postgres.models import Rooms
from dino.db.postgres.models import RoomRoles
from dino.db.postgres.models import ChannelRoles
from dino.db.postgres.models import Users
from dino.db.postgres.models import UserStatus
from dino.db.postgres.models import Channels

from dino.exceptions import NoSuchChannelException
from dino.exceptions import ChannelExistsException
from dino.exceptions import RoomExistsException
from dino.exceptions import NoSuchRoomException
from dino.exceptions import NoSuchUserException
from dino.exceptions import UserExistsException

from datetime import datetime

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


def with_session(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        session = DatabasePostgres.db.Session()
        try:
            _self = args[0]
            _self.__dict__.update({'session': session})
            return f(*args, **kwargs)
        except:
            session.rollback()
            raise
        finally:
            session.close()
    return wrapped


@implementer(IDatabase)
class DatabasePostgres(object):
    def __init__(self, env):
        self.env = env
        if self.env.config.get(ConfigKeys.TESTING, False):
            DatabasePostgres.db = MockDatabase()
        else:
            DatabasePostgres.db = Database(env)

    @with_session
    def _session(self):
        return self.session

    @with_session
    def room_exists(self, channel_id: str, room_id: str) -> bool:
        exists = self.env.cache.get_room_exists(channel_id, room_id)
        if exists is not None:
            return exists

        rooms = self.session.query(Rooms)\
            .filter(Rooms.uuid == room_id)\
            .all()

        exists = len(rooms) > 0
        if exists:
            self.env.cache.set_room_exists(channel_id, room_id, rooms[0].name)
        return exists

    @with_session
    def get_user_status(self, user_id: str) -> None:
        status = self.env.cache.get_user_status(user_id)
        if status is not None:
            return status

        status = self.session.query(UserStatus).filter(Users.uuid == user_id).first()
        if status is None:
            return UserStatus.STATUS_UNKNOWN
        return status.status

    @with_session
    def set_user_invisible(self, user_id: str) -> None:
        if self.env.cache.user_is_invisible(user_id):
            return

        self.env.cache.set_user_invisible(user_id)
        self.session.query(UserStatus).filter_by(uuid=user_id).update({'status': UserStatus.STATUS_INVISIBLE})
        self.session.commit()

    @with_session
    def set_user_offline(self, user_id: str) -> None:
        if self.env.cache.user_is_offline(user_id):
            return

        self.env.cache.set_user_offline(user_id)
        status = self.session.query(UserStatus).filter_by(uuid=user_id).first()
        self.session.delete(status)
        self.session.commit()

    @with_session
    def set_user_online(self, user_id: str) -> None:
        if self.env.cache.user_is_online(user_id):
            return

        self.env.cache.set_user_online(user_id)
        self.session.query(UserStatus).filter_by(uuid=user_id).update({'status': UserStatus.STATUS_AVAILABLE})
        self.session.commit()

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

    @with_session
    def room_name_exists(self, channel_id, room_name: str) -> bool:
        exists = self.env.cache.get_room_id_for_name(channel_id, room_name)
        if exists is not None:
            return exists

        rows = self.session.query(Rooms).filter(Rooms.name == room_name).all()
        exists = len(rows) > 0

        # only set in cache if actually exists, otherwise duplicates could be created
        if exists:
            self.env.cache.set_room_id_for_name(channel_id, room_name, rows[0].uuid)

        return exists

    @with_session
    def channel_exists(self, channel_id) -> bool:
        exists = self.env.cache.get_channel_exists(channel_id)
        if exists is not None:
            return exists

        rows = self.session.query(Channels).filter(Channels.uuid == channel_id).all()
        exists = len(rows) > 0

        # only set in cache if actually exists, otherwise duplicates could be created
        if exists:
            self.env.cache.set_channel_exists(channel_id)

        return exists

    @with_session
    def create_channel(self, channel_name, channel_id, user_id):
        if self.channel_exists(channel_id):
            raise ChannelExistsException(channel_id)

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

    @with_session
    def create_room(self, room_name: str, room_id: str, channel_id: str, user_id: str, user_name: str) -> None:
        if self.room_exists(channel_id, room_id):
            raise RoomExistsException(room_id)

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
        raise NotImplementedError()

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

    @with_session
    def room_owners_contain(self, room_id, user_id) -> bool:
        room = self.session.query(Rooms).join(Rooms.roles).filter(Rooms.uuid == room_id).first()
        if room is None:
            return False

        found_role = None
        for role in room.roles:
            if role.user_id == user_id:
                found_role = role
                break

        if found_role is None:
            return None
        if found_role.roles is None or found_role.roles == '':
            return False

        return RoleKeys.OWNER in set(found_role.roles.split(','))

    @with_session
    def is_admin(self, user_id: str) -> bool:
        # TODO: need to revise roles first
        # TODO: cache
        raise NotImplementedError()

    @with_session
    def delete_acl(self, room_id: str, acl_type: str) -> None:
        raise NotImplementedError()

    @with_session
    def add_acls(self, room_id: str, acls: dict) -> None:
        raise NotImplementedError()

    @with_session
    def get_acls(self, room_id: str) -> list:
        raise NotImplementedError()
