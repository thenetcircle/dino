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

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Integer, Column, ForeignKey

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

DeclarativeBase = declarative_base()

rooms_users_association_table = Table(
        'rooms_users_association_table',
        DeclarativeBase.metadata,
        Column('room_id', Integer, ForeignKey('rooms.id')),
        Column('user_id', Integer, ForeignKey('users.id'))
)
