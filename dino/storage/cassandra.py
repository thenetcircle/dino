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

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


@implementer(IStorage)
class CassandraStorage(object):
    session = None
    key_space = 'dino'

    insert_msg_statement = None
    insert_room_statement = None
    select_message_statement = None

    def __init__(self, hosts: list, replications=2, strategy='SimpleStrategy'):
        CassandraStorage.validate(hosts, replications, strategy)

        cluster = Cluster(hosts)
        self.session = cluster.connect()

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
                PRIMARY KEY ((from_user, to_user), time)
            )
            """
        )
        self.session.execute(
            """
            CREATE TABLE IF NOT EXISTS rooms (
                room_id uuid,
                room_name varchar,
                owners list,
                time varchar,
                PRIMARY KEY (room_id)
            )
            """
        )

    def prepare_statements(self):
        self.insert_msg_statement = self.session.prepare(
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
        self.insert_room_statement = self.session.prepare(
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
        self.select_message_statement = self.session.prepare(
            """
            SELECT FROM rooms where room_id = ?
            """
        )

    def store_message(self, activity: Activity) -> None:
        self.session.execute(self.insert_msg_statement.bind((
            activity.id,
            activity.actor.id,
            activity.target.id,
            activity.object.content,
            activity.published,
            activity.target.object_type
        )))

    def create_room(self, activity: Activity) -> None:
        self.session.execute(self.insert_room_statement.bind((
            activity.target.id,
            activity.target.display_name,
            [activity.actor.id],
            activity.published
        )))

    def delete_acl(self, room_id: str, acl_type: str) -> None:
        pass

    def add_acls(self, room_id: str, acls: dict) -> None:
        pass

    def get_acls(self, room_id: str) -> list:
        pass

    def get_history(self, room_id: str, limit: int=None):
        self.session.execute(self.select_message_statement.bind((room_id, )))

    def set_user_offline(self, user_id: str) -> None:
        pass

    def set_user_online(self, user_id: str) -> None:
        pass

    def set_user_invisible(self, user_id: str) -> None:
        pass

    def get_room_name(self, room_id: str) -> str:
        pass

    def join_room(self, user_id: str, user_name: str, room_id: str, room_name: str) -> None:
        pass

    def users_in_room(self, room_id: str) -> list:
        pass

    def get_all_rooms(self, user_id: str=None) -> dict:
        pass

    def leave_room(self, user_id: str, room_id: str) -> None:
        pass

    def remove_current_rooms_for_user(self, user_id: str) -> None:
        pass

    def room_exists(self, room_id: str) -> bool:
        pass

    def room_name_exists(self, room_name: str) -> bool:
        pass

    def room_contains(self, room_id: str, user_id: str) -> bool:
        pass

    def get_owners(self, room_id: str) -> dict:
        pass

    def room_owners_contain(self, room_id: str, user_id: str) -> bool:
        pass

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
