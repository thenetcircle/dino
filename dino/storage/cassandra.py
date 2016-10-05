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

from zope.interface import implementer
from activitystreams.models.activity import Activity
from cassandra.cluster import Cluster

from dino.storage.base import IStorage
from dino.env import env
from dino.env import ConfigKeys
from enum import Enum

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class StatementKeys(Enum):
    msg_insert = 'msg_insert'
    msgs_select = 'msgs_select'
    room_insert = 'room_insert'
    room_delete = 'room_delete'
    room_select_name = 'room_select_name'
    room_select_users = 'room_select_users'
    room_delete_user = 'room_delete_user'
    room_insert_user = 'room_insert_user'
    rooms_select = 'rooms_select'


@implementer(IStorage)
class CassandraStorage(object):
    session = None
    key_space = 'dino'

    def __init__(self, hosts: list, replications=2, strategy='SimpleStrategy'):
        if replications is None:
            replications = 2
        if strategy is None:
            strategy = 'SimpleStrategy'

        CassandraStorage.validate(hosts, replications, strategy)

        cluster = Cluster(hosts)
        self.session = cluster.connect()

        self.statements = dict()

        self.create_keyspace(strategy, replications)
        self.create_tables()
        self.prepare_statements()

    def create_keyspace(self, strategy, replications):
        env.logger.debug('creating keyspace...')
        create_keyspace = self.session.prepare(
            """
            CREATE KEYSPACE IF NOT EXISTS %s
            WITH replication = {'class': '%s', 'replication_factor': '%s'}
            """ % (CassandraStorage.key_space, strategy, str(replications))
        )
        self.session.execute(create_keyspace)
        self.session.set_keyspace(CassandraStorage.key_space)

    def create_tables(self):
        env.logger.debug('creating tables...')
        self.session.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                message_id uuid,
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
                room_id uuid,
                room_name varchar,
                owners list<uuid>,
                time varchar,
                PRIMARY KEY (room_id)
            )
            """
        )
        self.session.execute(
            """
            CREATE TABLE IF NOT EXISTS users_in_room (
                room_id uuid,
                user_id uuid,
                user_name uuid,
                PRIMARY KEY (room_id, user_id)
            )
            """
        )

    def prepare_statements(self):
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
            INSERT INTO users_in_room(room_id, user_id, user_name) VALUES(?, ?, ?)
            """
        )
        self.statements[StatementKeys.room_delete_user] = self.session.prepare(
            """
            DELETE FROM users_in_room WHERE room_id = ? AND user_id = ?
            """
        )

    def store_message(self, activity: Activity) -> None:
        self.session.execute(self.statements[StatementKeys.msg_insert].bind((
            activity.id,
            activity.actor.id,
            activity.target.id,
            activity.object.content,
            activity.published,
            activity.target.object_type
        )))

    def create_room(self, activity: Activity) -> None:
        self.session.execute(self.statements[StatementKeys.room_insert].bind((
            activity.target.id,
            activity.target.display_name,
            [activity.actor.id],
            activity.published
        )))

    def delete_acl(self, room_id: str, acl_type: str) -> None:
        raise NotImplementedError()

    def add_acls(self, room_id: str, acls: dict) -> None:
        raise NotImplementedError()

    def get_acls(self, room_id: str) -> list:
        raise NotImplementedError()

    def get_history(self, room_id: str, limit: int=None):
        self.session.execute(self.statements[StatementKeys.msgs_select].bind((room_id, )))

    def set_user_offline(self, user_id: str) -> None:
        raise NotImplementedError()

    def set_user_online(self, user_id: str) -> None:
        raise NotImplementedError()

    def set_user_invisible(self, user_id: str) -> None:
        raise NotImplementedError()

    def get_room_name(self, room_id: str) -> str:
        return self.session.execute(self.statements[StatementKeys.room_select_name].bind((room_id, )))

    def join_room(self, user_id: str, user_name: str, room_id: str, room_name: str) -> None:
        self.session.execute(self.statements[StatementKeys.room_insert_user].bind((room_id, user_id, user_name)))

    def users_in_room(self, room_id: str) -> list:
        return self.session.execute(self.statements[StatementKeys.room_select_users].bind((room_id, )))

    def get_all_rooms(self, user_id: str=None) -> dict:
        return self.session.execute(self.statements[StatementKeys.rooms_select])

    def leave_room(self, user_id: str, room_id: str) -> None:
        self.session.execute(self.statements[StatementKeys.room_delete_user].bind((room_id, user_id)))

    def remove_current_rooms_for_user(self, user_id: str) -> None:
        raise NotImplementedError()

    def room_exists(self, room_id: str) -> bool:
        raise NotImplementedError()

    def room_name_exists(self, room_name: str) -> bool:
        raise NotImplementedError()

    def room_contains(self, room_id: str, user_id: str) -> bool:
        raise NotImplementedError()

    def get_owners(self, room_id: str) -> dict:
        return self.session.execute(self.statements[StatementKeys.room_select_owners].bind((room_id, )))

    def room_owners_contain(self, room_id: str, user_id: str) -> bool:
        raise NotImplementedError()

    @staticmethod
    def validate(hosts, replications, strategy):
        if env.config.get(ConfigKeys.TESTING, False):
            raise NotImplementedError('mocking with cassandra not implemented, mock using redis storage instead')

        if not isinstance(replications, int):
            raise ValueError('replications is not a valid int: "%s"' % str(replications))
        if replications < 1 or replications > 99:
            raise ValueError('replications needs to be in the interval [1, 99]')

        if replications > len(hosts):
            env.logger.warn('replications (%s) is higher than number of nodes in cluster (%s)' %
                            (len(hosts), str(replications)))

        if not isinstance(strategy, str):
            raise ValueError('strategy is not a valid string, but of type: "%s"' % str(type(strategy)))

        valid_strategies = ['SimpleStrategy', 'NetworkTopologyStrategy']
        if strategy not in valid_strategies:
            raise ValueError('unknown strategy "%s", valid strategies are: %s' %
                             (str(strategy), ', '.join(valid_strategies)))
