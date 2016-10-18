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
from dino.db import IDatabase
from dino.db.postgres.dbman import Database
from dino.db.postgres.mock import MockDatabase
from dino.db.postgres.models import Rooms
from dino.db.postgres.models import Users
from dino.db.postgres.models import UserStatus
from dino.db.postgres.models import Channels

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
    def room_exists(self, channel_id: str, room_id: str) -> bool:
        exists = self.env.cache.get_room_exists(room_id)
        if exists is not None:
            return exists

        rooms = self.session.query(Rooms)\
            .filter(Rooms.uuid == room_id)\
            .all()

        exists = len(rooms) > 0
        if exists:
            self.env.cache.set_room_exists(room_id, True)
        return exists

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
        rows = self.session.query(Rooms).join(Users).filter(Users.uuid == user_id).all()
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
        for row in rows:
            self.session.delete(row)

    @with_session
    def get_channels(self) -> dict:
        # TODO: cache
        rows = self.session.query(Channels).all()
        channels = dict()
        for row in rows:
            channels[row.uuid] = row.name
        return channels

    @with_session
    def room_name_exists(self, channel_id, room_name: str) -> bool:
        # TODO: cache
        rows = self.session.query(Rooms).filter(Rooms.name == room_name).all()
        return len(rows) > 0

    @with_session
    def channel_exists(self, channel_id) -> bool:
        # TODO: cache
        rows = self.session.query(Channels).filter(Channels.uuid == channel_id).all()
        return len(rows) > 0

    @with_session
    def room_owners_contain(self, room_id, user_id) -> bool:
        # TODO: need to revise roles first
        raise NotImplementedError()

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
