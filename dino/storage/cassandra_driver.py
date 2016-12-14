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

import logging

from cassandra.cluster import ResultSet
from cassandra.cluster import Session
from dino.storage.cassandra_interface import IDriver
from enum import Enum
from zope.interface import implementer

from dino.config import ConfigKeys
from datetime import datetime

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class StatementKeys(Enum):
    msg_insert = 'msg_insert'
    msg_select = 'msg_select'
    msgs_select = 'msgs_select'
    msgs_select_by_time_stamp = 'msgs_select_by_time_stamp'
    msg_select_one = 'msg_select_one'


@implementer(IDriver)
class Driver(object):
    def __init__(self, session: Session, key_space: str, strategy: str, replications: int):
        self.session = session
        self.statements = dict()
        self.key_space = key_space
        self.key_space_test = key_space + 'test'
        self.strategy = strategy
        self.replications = replications
        self.logger = logging.getLogger(__name__)

    def init(self):
        def create_test_key_space():
            self.logger.debug('creating test keyspace...')
            create_key_space_stmt = self.session.prepare(
                    """
                    CREATE KEYSPACE IF NOT EXISTS %s
                    WITH replication = {'class': '%s', 'replication_factor': '%s'}
                    """ % (self.key_space + 'test', self.strategy, str(self.replications))
            )
            self.session.execute(create_key_space_stmt)

        def create_key_space():
            self.logger.debug('creating keyspace...')
            create_key_space_stmt = self.session.prepare(
                    """
                    CREATE KEYSPACE IF NOT EXISTS %s
                    WITH replication = {'class': '%s', 'replication_factor': '%s'}
                    """ % (self.key_space, self.strategy, str(self.replications))
            )
            self.session.execute(create_key_space_stmt)

        def set_key_space():
            self.logger.debug('switching to key space: %s' % self.key_space)
            self.session.set_keyspace(self.key_space)

        def set_test_key_space():
            self.logger.debug('switching to key space: %s' % self.key_space_test)
            self.session.set_keyspace(self.key_space_test)

        def create_tables():
            self.logger.debug('creating tables...')
            self.session.execute(
                    """
                    CREATE TABLE IF NOT EXISTS messages (
                        message_id varchar,
                        from_user_id text,
                        from_user_name text,
                        target_id text,
                        target_name text,
                        body text,
                        domain text,
                        sent_time varchar,
                        time_stamp int,
                        channel_id varchar,
                        channel_name text,
                        deleted boolean,
                        PRIMARY KEY (target_id, from_user_id, sent_time, time_stamp)
                    )
                    """
            )

        def create_views():
            self.session.execute(
                    """
                    CREATE MATERIALIZED VIEW IF NOT EXISTS messages_by_id AS
                        SELECT * from messages
                            WHERE
                                message_id IS NOT NULL AND
                                target_id IS NOT NULL AND
                                from_user_id IS NOT NULL AND
                                sent_time IS NOT NULL AND
                                time_stamp IS NOT NULL
                        PRIMARY KEY (message_id, target_id, from_user_id, sent_time, time_stamp)
                        WITH CLUSTERING ORDER BY (time_stamp DESC)
                    """
            )
            self.session.execute(
                    """
                    CREATE MATERIALIZED VIEW IF NOT EXISTS messages_by_time_stamp AS
                        SELECT * from messages
                            WHERE
                                message_id IS NOT NULL AND
                                body IS NOT NULL AND
                                target_id IS NOT NULL AND
                                from_user_id IS NOT NULL AND
                                sent_time IS NOT NULL AND
                                time_stamp IS NOT NULL
                        PRIMARY KEY (target_id, time_stamp, from_user_id, sent_time)
                        WITH CLUSTERING ORDER BY (time_stamp DESC)
                    """
            )
            self.session.execute(
                    """
                    CREATE MATERIALIZED VIEW IF NOT EXISTS messages_by_from_user_id AS
                        SELECT * from messages
                            WHERE
                                message_id IS NOT NULL AND
                                body IS NOT NULL AND
                                target_id IS NOT NULL AND
                                from_user_id IS NOT NULL AND
                                sent_time IS NOT NULL AND
                                time_stamp IS NOT NULL
                        PRIMARY KEY (from_user_id, target_id, time_stamp)
                        WITH CLUSTERING ORDER BY (time_stamp DESC)
                    """
            )

        def prepare_statements():
            self.statements[StatementKeys.msg_insert] = self.session.prepare(
                    """
                    INSERT INTO messages (
                        message_id,
                        from_user_id,
                        from_user_name,
                        target_id,
                        target_name,
                        body,
                        domain,
                        sent_time,
                        time_stamp,
                        channel_id,
                        channel_name,
                        deleted
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """
            )
            self.statements[StatementKeys.msgs_select] = self.session.prepare(
                    """
                    SELECT * FROM messages WHERE target_id = ? LIMIT ?
                    """
            )
            self.statements[StatementKeys.msgs_select_by_time_stamp] = self.session.prepare(
                    """
                    SELECT * FROM messages_by_time_stamp WHERE target_id = ? AND time_stamp > ?
                    """
            )
            self.statements[StatementKeys.msg_select] = self.session.prepare(
                    """
                    SELECT target_id, from_user_id, sent_time FROM messages_by_id WHERE message_id = ?
                    """
            )
            self.statements[StatementKeys.msg_select_one] = self.session.prepare(
                    """
                    SELECT * FROM messages WHERE target_id = ? AND from_user_id = ? AND sent_time = ?
                    """
            )

        # create keyspace and tables for tests
        create_test_key_space()
        set_test_key_space()
        create_tables()
        create_views()

        # create keyspace and tables for other
        create_key_space()
        set_key_space()
        create_tables()
        create_views()
        prepare_statements()

    def msg_insert(self, msg_id, from_user_id, from_user_name, target_id, target_name, body, domain, sent_time, channel_id, channel_name, deleted=False) -> None:
        time_stamp = int(datetime.strptime(sent_time, ConfigKeys.DEFAULT_DATE_FORMAT).strftime('%s'))
        self._execute(
                StatementKeys.msg_insert, msg_id, from_user_id, from_user_name, target_id, target_name,
                body, domain, sent_time, time_stamp, channel_id, channel_name, deleted)

    def msgs_select(self, target_id: str, limit: int=100) -> ResultSet:
        return self._execute(StatementKeys.msgs_select, target_id, limit)

    def msgs_select_since_time(self, target_id: str, time_stamp: int) -> ResultSet:
        return self._execute(StatementKeys.msgs_select_by_time_stamp, target_id, time_stamp)

    def msg_delete(self, message_id: str) -> ResultSet:
        """
        We're doing three queries here, one to get primary index of messages table from message_id, then getting the
        complete row from messages table, and finally updating that row. This could be lowered to two queries by
        duplicating everything from messages table to messages_by_id materialized view, but would also double storage
        requirements. Since message deletion is likely not a frequent operation we can accept doing three queries.

        :param message_id: the uuid of the message to 'delete' (will only flag as deleted, will not remove)
        """
        keys = self._execute(StatementKeys.msg_select, message_id)
        if keys is None or len(keys.current_rows) == 0:
            # not found
            return

        assert len(keys.current_rows) == 1
        key = keys.current_rows[0]
        target_id, from_user_id, timestamp = key.target_id, key.from_user_id, key.sent_time

        message_rows = self._execute(StatementKeys.msg_select_one, target_id, from_user_id, timestamp)
        assert len(message_rows.current_rows) == 1

        message_row = message_rows.current_rows[0]
        body = message_row.body
        domain = message_row.domain
        channel_id = message_row.channel_id
        channel_name = message_row.channel_name
        target_name = message_row.target_name
        from_user_name = message_row.from_user_name

        self.msg_insert(
                message_id, from_user_id, from_user_name, target_id, target_name, body,
                domain, timestamp, channel_id, channel_name, deleted=True)

    def _execute(self, statement_key, *params) -> ResultSet:
        if params is not None and len(params) > 0:
            return self.session.execute(self.statements[statement_key].bind(params))
        return self.session.execute(self.statements[statement_key])
