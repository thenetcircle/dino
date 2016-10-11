#!/usr/bin/env python

# Copyright 2013-2016 DataStax, Inc.
#
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

from cassandra.cluster import ResultSet
from cassandra.cluster import Session
from enum import Enum

from dino.env import env
from dino.validator import SessionKeys

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class StatementKeys(Enum):
    msg_insert = 'msg_insert'
    msgs_select = 'msgs_select'
    acl_insert = 'acl_insert'
    acl_select = 'acl_select'
    room_insert = 'room_insert'
    room_delete = 'room_delete'
    room_select_name = 'room_select_name'
    room_select_users = 'room_select_users'
    rooms_select_by_user = 'rooms_select_by_user'
    room_delete_user = 'rooms_select_by_user'
    room_insert_user = 'room_insert_user'
    room_select_owners = 'room_select_owners'
    rooms_select = 'rooms_select'


class Driver(object):
    def __init__(self, session: Session, key_space: str, strategy: str, replications: int):
        self.session = session
        self.statements = dict()
        self.key_space = key_space
        self.strategy = strategy
        self.replications = replications

    def init(self):
        def create_keyspace():
            env.logger.debug('creating keyspace...')
            create_keyspace = self.session.prepare(
                """
                CREATE KEYSPACE IF NOT EXISTS %s
                WITH replication = {'class': '%s', 'replication_factor': '%s'}
                """ % (self.key_space, self.strategy, str(self.replications))
            )
            self.session.execute(create_keyspace)
            self.session.set_keyspace(self.key_space)

        def create_tables():
            env.logger.debug('creating tables...')
            self.session.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    message_id varchar,
                    from_user text,
                    to_user text,
                    body text,
                    domain text,
                    time varchar,
                    PRIMARY KEY (to_user, from_user, time)
                )
                """
            )
            self.session.execute(
                """
                CREATE TABLE IF NOT EXISTS rooms (
                    room_id varchar,
                    room_name varchar,
                    owners list<varchar>,
                    time varchar,
                    PRIMARY KEY (room_id)
                )
                """
            )
            self.session.execute(
                """
                CREATE TABLE IF NOT EXISTS users_in_room (
                    room_id varchar,
                    room_name varchar,
                    user_id varchar,
                    user_name varchar,
                    PRIMARY KEY (room_id, user_id)
                )
                """
            )
            self.session.execute(
                """
                CREATE MATERIALIZED VIEW IF NOT EXISTS users_in_room_by_user AS
                    SELECT * from users_in_room
                        WHERE user_id IS NOT NULL AND room_id IS NOT NULL
                    PRIMARY KEY (user_id, room_id)
                    WITH comment='allows query by user_id instead of room_id'
                """
            )
            self.session.execute(
                """
                CREATE TABLE IF NOT EXISTS acl (
                    room_id varchar,
                    age varchar,
                    gender varchar,
                    membership varchar,
                    group varchar,
                    country varchar,
                    city varchar,
                    image varchar,
                    has_webcam varchar,
                    fake_checked varchar,
                    PRIMARY KEY (room_id)
                )
                """
            )

        def prepare_statements():
            self.statements[StatementKeys.msg_insert] = self.session.prepare(
                """
                INSERT INTO messages (
                    message_id,
                    from_user,
                    to_user,
                    body,
                    domain,
                    time
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?
                )
                """
            )
            self.statements[StatementKeys.acl_insert] = self.session.prepare(
                """
                INSERT INTO acl (
                    room_id,
                    age,
                    gender,
                    membership,
                    group,
                    country,
                    city,
                    image,
                    has_webcam,
                    fake_checked
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """
            )
            self.statements[StatementKeys.acl_select] = self.session.prepare(
                """
                SELECT * FROM acl WHERE room_id = ?
                """
            )
            self.statements[StatementKeys.room_insert] = self.session.prepare(
                """
                INSERT INTO rooms (
                    room_id,
                    room_name,
                    owners,
                    time
                )
                VALUES (
                    ?, ?, ?, ?
                )
                """
            )
            self.statements[StatementKeys.msgs_select] = self.session.prepare(
                """
                SELECT * FROM messages where to_user = ?
                """
            )
            self.statements[StatementKeys.rooms_select] = self.session.prepare(
                """
                SELECT * FROM rooms
                """
            )
            self.statements[StatementKeys.rooms_select_by_user] = self.session.prepare(
                """
                SELECT * FROM users_in_room_by_user WHERE user_id = ?
                """
            )
            self.statements[StatementKeys.room_select_name] = self.session.prepare(
                """
                SELECT room_name FROM rooms WHERE room_id = ?
                """
            )
            self.statements[StatementKeys.room_select_users] = self.session.prepare(
                """
                SELECT user_id, user_name FROM users_in_room WHERE room_id = ?
                """
            )
            self.statements[StatementKeys.room_insert_user] = self.session.prepare(
                """
                INSERT INTO users_in_room(room_id, room_name, user_id, user_name) VALUES(?, ?, ?, ?)
                """
            )
            self.statements[StatementKeys.room_select_owners] = self.session.prepare(
                """
                SELECT owners FROM rooms WHERE room_id = ?
                """
            )
            self.statements[StatementKeys.room_delete_user] = self.session.prepare(
                """
                DELETE FROM users_in_room WHERE room_id = ? AND user_id = ?
                """
            )

        create_keyspace()
        create_tables()
        prepare_statements()

    def acl_insert(self, room_id: str, acls: dict) -> None:
        self.execute(
            StatementKeys.acl_insert,
            room_id,
            acls.get(SessionKeys.age.value, None),
            acls.get(SessionKeys.gender.value, None),
            acls.get(SessionKeys.membership.value, None),
            acls.get(SessionKeys.group.value, None),
            acls.get(SessionKeys.country.value, None),
            acls.get(SessionKeys.city.value, None),
            acls.get(SessionKeys.image.value, None),
            acls.get(SessionKeys.has_webcam.value, None),
            acls.get(SessionKeys.fake_checked.value, None)
        )

    def acl_select(self, room_id: str) -> ResultSet:
        return self.execute(StatementKeys.acl_select, room_id)

    def room_select_owners(self, room_id: str) -> ResultSet:
        return self.execute(StatementKeys.room_select_owners, room_id)

    def rooms_select_for_user(self, user_id: str) -> ResultSet:
        return self.execute(StatementKeys.rooms_select_by_user, user_id)

    def msg_insert(self, msg_id, from_user, to_user, body, domain, timestamp) -> None:
        self.execute(StatementKeys.msg_insert, msg_id, from_user, to_user, body, domain, timestamp)

    def room_insert(self, room_id: str, room_name: str, owners: list, timestamp: str) -> None:
        self.execute(StatementKeys.room_insert, room_id, room_name, owners, timestamp)

    def msgs_select(self, to_user_id: str) -> ResultSet:
        return self.execute(StatementKeys.msgs_select, to_user_id)

    def rooms_select(self) -> ResultSet:
        return self.execute(StatementKeys.rooms_select)

    def room_select_name(self, room_id: str) -> ResultSet:
        return self.execute(StatementKeys.room_select_name, room_id)

    def room_select_users(self, room_id: str) -> ResultSet:
        return self.execute(StatementKeys.room_select_users, room_id)

    def room_insert_user(self, room_id: str, room_name: str, user_id: str, user_name: str) -> None:
        self.execute(StatementKeys.room_insert_user, room_id, room_name, user_id, user_name)

    def room_delete_user(self, room_id: str, user_id: str) -> None:
        self.execute(StatementKeys.room_delete_user, room_id, user_id)

    def execute(self, statement_key, *params) -> ResultSet:
        if params is not None and len(params) > 0:
            return self.session.execute(self.statements[statement_key].bind(params))
        return self.session.execute(self.statements[statement_key])
