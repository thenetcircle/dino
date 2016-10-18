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

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from dino.db.postgres import DeclarativeBase
from dino.db.postgres import rooms_users_association_table

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


@staticmethod
class UserStatus(DeclarativeBase):
    __tablename__ = 'user_status'

    STATUS_AVAILABLE = '1'
    STATUS_CHAT = '2'
    STATUS_INVISIBLE = '3'
    STATUS_UNAVAILABLE = '4'
    STATUS_UNKNOWN = '5'

    id = Column(Integer, primary_key=True)
    uuid = Column('uuid', String, nullable=False, index=True, unique=True)
    status = Column('status', Integer, nullable=False, default=STATUS_UNKNOWN)


class Channels(DeclarativeBase):
    __tablename__ = 'channels'

    id = Column(Integer, primary_key=True)
    uuid = Column('uuid', String, nullable=False, index=True)
    name = Column('name', String, nullable=False)
    created = Column('created', DateTime, nullable=False)

    rooms = relationship('Rooms', back_populates='channel')


class Rooms(DeclarativeBase):
    __tablename__ = 'rooms'

    id = Column(Integer, primary_key=True)
    uuid = Column('uuid', String, nullable=False, index=True)
    name = Column('name', String, nullable=False, index=True)
    created = Column('created', DateTime, nullable=False)

    channel_id = Column('channel_id', Integer, ForeignKey('channels.id'), nullable=False)
    channel = relationship('Channels', back_populates='rooms')

    acls = relationship('Acls', back_populates='room')
    roles = relationship('Roles', back_populates='room')

    users = relationship(
        'Users',
        secondary=rooms_users_association_table,
        back_populates='rooms')


class Users(DeclarativeBase):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    uuid = Column('uuid', String, nullable=False, index=True)
    name = Column('name', String, nullable=False)

    rooms = relationship(
        'Rooms',
        secondary=rooms_users_association_table,
        back_populates='users')


class Acls(DeclarativeBase):
    __tablename__ = 'acls'

    id = Column(Integer, primary_key=True)

    room_id = Column('room_id', Integer, ForeignKey('rooms.id'), nullable=False)
    room = relationship('Rooms', back_populates='acls')

    age = Column('age', Integer, nullable=True)
    gender = Column('gender', String, nullable=True)
    membership = Column('membership', String, nullable=True)
    group = Column('group', String, nullable=True)
    country = Column('country', String, nullable=True)
    city = Column('city', String, nullable=True)
    image = Column('image', String, nullable=True)
    has_webcam = Column('has_webcam', String, nullable=True)
    fake_checked = Column('fake_checked', String, nullable=True)


class Roles(DeclarativeBase):
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True)

    room_id = Column('room_id', Integer, ForeignKey('rooms.id'), nullable=False)
    room = relationship('Rooms', back_populates='roles')

    user_id = Column('user_id', String(128), nullable=False, index=True)
    roles = Column('roles', String(256), nullable=False)
