#!/usr/bin/env python

# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from dino.db.rdbms import DeclarativeBase
from dino.db.rdbms import rooms_users_association_table
from dino.config import UserKeys

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class UserStatus(DeclarativeBase):
    __tablename__ = 'user_status'

    id = Column(Integer, primary_key=True)
    uuid = Column('uuid', String(128), nullable=False, index=True, unique=True)
    status = Column('status', Integer, nullable=False, default=UserKeys.STATUS_UNKNOWN)


class Channels(DeclarativeBase):
    __tablename__ = 'channels'

    id = Column(Integer, primary_key=True)
    uuid = Column('uuid', String(128), nullable=False, index=True)
    name = Column('name', String(128), nullable=False)
    created = Column('created', DateTime, nullable=False)

    rooms = relationship('Rooms', back_populates='channel')
    roles = relationship('ChannelRoles', back_populates='channel')
    bans = relationship('Bans', back_populates='channel')
    acls = relationship('Acls', back_populates='channel')


class Rooms(DeclarativeBase):
    __tablename__ = 'rooms'

    id = Column(Integer, primary_key=True)
    uuid = Column('uuid', String(128), nullable=False, index=True)
    name = Column('name', String(128), nullable=False, index=True)
    created = Column('created', DateTime, nullable=False)
    admin = Column('admin', Boolean, nullable=False, default=True, index=True)

    channel_id = Column('channel_id', Integer, ForeignKey('channels.id'), nullable=False)
    channel = relationship('Channels', back_populates='rooms')

    roles = relationship('RoomRoles', back_populates='room')
    bans = relationship('Bans', back_populates='room')
    acls = relationship('Acls', back_populates='room')

    users = relationship(
        'Users',
        secondary=rooms_users_association_table,
        back_populates='rooms')


class Bans(DeclarativeBase):
    __tablename__ = 'bans'

    id = Column(Integer, primary_key=True)
    uuid = Column('uuid', String(128), nullable=False, index=True, unique=True)
    user_id = Column('user_id', String(128), nullable=False, index=True)
    user_name = Column('user_name', String(128), nullable=True, index=False)
    duration = Column('duration', String(128), nullable=False)
    timestamp = Column('time_stamp', DateTime, nullable=False)

    reason = Column('reason', String(256), nullable=True)
    banner_id = Column('banner_id', String(128), nullable=True)

    room_id = Column('room_id', Integer, ForeignKey('rooms.id'), nullable=True)
    room = relationship('Rooms', back_populates='bans')

    channel_id = Column('channel_id', Integer, ForeignKey('channels.id'), nullable=True)
    channel = relationship('Channels', back_populates='bans')

    is_global = Column('is_global', Boolean, nullable=False, index=True, default=False)


class Users(DeclarativeBase):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    uuid = Column('uuid', String(128), nullable=False, index=True)
    name = Column('name', String(128), nullable=False)
    sid = Column('session_id', String(128), nullable=True)

    rooms = relationship(
        'Rooms',
        secondary=rooms_users_association_table,
        back_populates='users')


class LastReads(DeclarativeBase):
    __tablename__ = 'lastreads'

    id = Column(Integer, primary_key=True)

    room_uuid = Column('room_uuid', String(128), nullable=False, index=True)
    user_id = Column('user_id', String(128), nullable=False, index=True)
    time_stamp = Column('time_stamp', Integer, nullable=False)


class Acls(DeclarativeBase):
    __tablename__ = 'acls'

    id = Column(Integer, primary_key=True)

    room_id = Column('room_id', Integer, ForeignKey('rooms.id'), nullable=True)
    room = relationship('Rooms', back_populates='acls')

    channel_id = Column('channel_id', Integer, ForeignKey('channels.id'), nullable=True)
    channel = relationship('Channels', back_populates='acls')

    # action: join/create/kick etc.
    action = Column('action', String(128), nullable=False)

    # acl_type: gender/age/city etc.
    acl_type = Column('acl_type', String(128), nullable=False)
    acl_value = Column('acl_value', String(128), nullable=False)


class AclConfigs(DeclarativeBase):
    __tablename__ = 'aclconfigs'

    id = Column(Integer, primary_key=True)

    # method: str_in_csv/range etc.
    method = Column('method', String(128), nullable=False)

    # acl_type: gender/age/city etc.
    acl_type = Column('acl_type', String(128), nullable=False)

    # acl_value: the configured value, e.g. 'm,f' for an acl_type 'gender'
    acl_value = Column('acl_value', String(128), nullable=False)


class BlackList(DeclarativeBase):
    __tablename__ = 'blacklist'

    id = Column(Integer, primary_key=True)
    word = Column('word', String(128), nullable=False)


class RoomRoles(DeclarativeBase):
    __tablename__ = 'room_roles'

    id = Column(Integer, primary_key=True)

    room_id = Column('room_id', Integer, ForeignKey('rooms.id'), nullable=False)
    room = relationship('Rooms', back_populates='roles')

    user_id = Column('user_id', String(128), nullable=False, index=True)
    roles = Column('roles', String(256), nullable=False)


class GlobalRoles(DeclarativeBase):
    __tablename__ = 'global_roles'

    id = Column(Integer, primary_key=True)
    user_id = Column('user_id', String(128), nullable=False, index=True)
    roles = Column('roles', String(256), nullable=False)


class ChannelRoles(DeclarativeBase):
    __tablename__ = 'channel_roles'

    id = Column(Integer, primary_key=True)

    channel_id = Column('channel_id', Integer, ForeignKey('channels.id'), nullable=False)
    channel = relationship('Channels', back_populates='roles')

    user_id = Column('user_id', String(128), nullable=False, index=True)
    roles = Column('roles', String(256), nullable=False)
