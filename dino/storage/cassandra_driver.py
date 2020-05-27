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
import pytz

from datetime import datetime
from enum import Enum

from cassandra.cluster import ResultSet
from cassandra.cluster import Session
from cassandra.query import ValueSequence

from dino.storage.cassandra_interface import IDriver
from dino.config import ConfigKeys

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


class StatementKeys(Enum):
    acks_update = 'acks_update'
    acks_insert = 'acks_insert'
    acks_get = 'acks_get'
    acks_get_for_status = 'acks_get_for_status'
    msg_insert = 'msg_insert'
    msg_update = 'msg_update'
    msg_select = 'msg_select'
    msg_select_all = 'msg_select_all'
    msgs_select = 'msgs_select'
    msgs_select_all_in = 'msgs_select_all_in'
    msgs_select_time_slice = 'msgs_select_time_slice'
    msgs_select_by_time_stamp = 'msgs_select_by_time_stamp'
    msgs_select_latest_non_deleted = 'msgs_select_latest_non_deleted'
    msgs_select_from_user = 'msg_select_from_user'
    msgs_select_from_user_to_target = 'msg_select_from_user_to_target'
    msgs_select_from_user_to_target_time_slice = 'msg_select_from_user_to_target_time_slice'
    msg_select_one = 'msg_select_one'
    msg_select_msg_id_from_user_not_deleted = 'msg_select_msg_id_from_user_not_deleted'
    msg_select_msg_id_from_user_all = 'msg_select_msg_id_from_user_all'
    msg_select_msgs_from_user_not_deleted_for_time = 'msg_select_msgs_from_user_not_deleted_for_time'
    msg_select_msg_id_from_user_and_room_not_deleted = 'msg_select_msg_id_from_user_and_room_not_deleted'


class Driver(IDriver):
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
            self.session.execute(
                """
                CREATE TABLE IF NOT EXISTS msg_acks (
                    for_user_id text, 
                    message_id varchar, 
                    status int, 
                    target_id varchar,
                    primary key(for_user_id, message_id)
                )
                """
            )

        def create_views():
            self.session.execute(
                    """
                    CREATE MATERIALIZED VIEW IF NOT EXISTS acks_by_user_and_status AS
                        SELECT * from msg_acks
                            WHERE
                                for_user_id IS NOT NULL AND
                                message_id IS NOT NULL AND
                                status IS NOT NULL AND
                                target_id IS NOT NULL
                        PRIMARY KEY (for_user_id, status, message_id)
                        WITH CLUSTERING ORDER BY (status DESC)
                    """
            )
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
                    CREATE MATERIALIZED VIEW IF NOT EXISTS messages_by_time_stamp_non_deleted AS
                        SELECT * from messages
                            WHERE
                                message_id IS NOT NULL AND
                                body IS NOT NULL AND
                                target_id IS NOT NULL AND
                                from_user_id IS NOT NULL AND
                                sent_time IS NOT NULL AND
                                deleted IS NOT NULL AND
                                time_stamp IS NOT NULL
                        PRIMARY KEY (target_id, deleted, time_stamp, from_user_id, sent_time)
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
                        PRIMARY KEY (from_user_id, target_id, time_stamp, sent_time)
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
            self.statements[StatementKeys.msg_update] = self.session.prepare(
                    """
                    UPDATE messages SET body = ?, deleted = ? 
                    WHERE 
                      target_id = ? AND 
                      from_user_id = ? AND
                      sent_time = ? AND
                      time_stamp = ?
                    """
            )
            self.statements[StatementKeys.acks_update] = self.session.prepare(
                """
                UPDATE msg_acks SET status = ? where for_user_id = ? and message_id in ?
                """
            )
            self.statements[StatementKeys.acks_insert] = self.session.prepare(
                """
                INSERT INTO msg_acks (for_user_id, message_id, status, target_id) values(?, ?, ?, ?)
                """
            )
            self.statements[StatementKeys.acks_get] = self.session.prepare(
                """
                SELECT * FROM msg_acks WHERE for_user_id = ? and message_id in ?
                """
            )
            self.statements[StatementKeys.acks_get_for_status] = self.session.prepare(
                """
                SELECT * FROM acks_by_user_and_status WHERE for_user_id = ? and status = ?
                """
            )
            self.statements[StatementKeys.msgs_select] = self.session.prepare(
                    """
                    SELECT * FROM messages WHERE target_id = ? LIMIT ?
                    """
            )
            self.statements[StatementKeys.msgs_select_all_in] = self.session.prepare(
                    """
                    SELECT * FROM messages_by_id WHERE message_id in ?
                    """
            )
            self.statements[StatementKeys.msgs_select_by_time_stamp] = self.session.prepare(
                    """
                    SELECT * FROM messages_by_time_stamp WHERE target_id = ? AND time_stamp > ?
                    """
            )
            self.statements[StatementKeys.msgs_select_latest_non_deleted] = self.session.prepare(
                    """
                    SELECT * FROM messages_by_time_stamp_non_deleted WHERE target_id = ? AND deleted = False LIMIT ?
                    """
            )
            self.statements[StatementKeys.msgs_select_time_slice] = self.session.prepare(
                    """
                    SELECT * FROM messages_by_time_stamp WHERE target_id = ? AND time_stamp > ? AND time_stamp < ?
                    """
            )
            self.statements[StatementKeys.msgs_select_from_user] = self.session.prepare(
                    """
                    SELECT * FROM messages_by_from_user_id WHERE from_user_id = ? LIMIT ?
                    """
            )
            self.statements[StatementKeys.msgs_select_from_user_to_target] = self.session.prepare(
                    """
                    SELECT * FROM messages_by_from_user_id WHERE from_user_id = ? AND target_id = ? LIMIT ?
                    """
            )
            self.statements[StatementKeys.msgs_select_from_user_to_target_time_slice] = self.session.prepare(
                    """
                    SELECT * FROM messages_by_from_user_id WHERE from_user_id = ? AND target_id = ? AND time_stamp > ? AND time_stamp < ? LIMIT ?
                    """
            )
            self.statements[StatementKeys.msg_select] = self.session.prepare(
                    """
                    SELECT target_id, from_user_id, sent_time FROM messages_by_id WHERE message_id = ?
                    """
            )
            self.statements[StatementKeys.msg_select_all] = self.session.prepare(
                    """
                    SELECT * FROM messages_by_id WHERE message_id = ?
                    """
            )
            self.statements[StatementKeys.msg_select_one] = self.session.prepare(
                    """
                    SELECT * FROM messages WHERE target_id = ? AND from_user_id = ? AND sent_time = ?
                    """
            )
            self.statements[StatementKeys.msg_select_msg_id_from_user_not_deleted] = self.session.prepare(
                    """
                    SELECT
                        message_id FROM messages_by_from_user_id
                    WHERE
                        from_user_id = ? AND
                        deleted = False AND
                        domain = 'room'
                    ALLOW FILTERING
                    """
            )
            self.statements[StatementKeys.msg_select_msg_id_from_user_all] = self.session.prepare(
                    """
                    SELECT
                        message_id FROM messages_by_from_user_id
                    WHERE
                        from_user_id = ? AND
                        domain = 'room'
                    ALLOW FILTERING
                    """
            )
            self.statements[StatementKeys.msg_select_msgs_from_user_not_deleted_for_time] = self.session.prepare(
                    """
                    SELECT
                        * FROM messages_by_from_user_id
                    WHERE
                        from_user_id = ? AND
                        deleted = False AND
                        domain = 'room' AND
                        time_stamp > ? AND
                        time_stamp < ?
                    ALLOW FILTERING
                    """
            )
            self.statements[StatementKeys.msg_select_msg_id_from_user_and_room_not_deleted] = self.session.prepare(
                    """
                    SELECT
                        message_id FROM messages_by_from_user_id
                    WHERE
                        from_user_id = ? AND
                        target_id = ? AND
                        deleted = False AND
                        domain = 'room'
                    ALLOW FILTERING
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
        dt = datetime.strptime(sent_time, ConfigKeys.DEFAULT_DATE_FORMAT)
        dt = pytz.timezone('utc').localize(dt, is_dst=None)
        time_stamp = int(dt.astimezone(pytz.utc).strftime('%s'))
        self._execute(
                StatementKeys.msg_insert, msg_id, from_user_id, from_user_name, target_id, target_name,
                body, domain, sent_time, time_stamp, channel_id, channel_name, deleted)

    def msg_update(self, from_user_id, target_id, body, sent_time, deleted=False) -> None:
        dt = datetime.strptime(sent_time, ConfigKeys.DEFAULT_DATE_FORMAT)
        dt = pytz.timezone('utc').localize(dt, is_dst=None)
        time_stamp = int(dt.astimezone(pytz.utc).strftime('%s'))
        self._execute(StatementKeys.msg_update, body, deleted, target_id, from_user_id, sent_time, time_stamp)

    def get_acks_for(self, message_ids: set, receiver_id: str) -> ResultSet:
        return self._execute(StatementKeys.acks_get, receiver_id, message_ids)

    def get_acks_for_status(self, user_id: str, status: int) -> ResultSet:
        return self._execute(StatementKeys.acks_get_for_status, user_id, status)

    def add_acks_with_status(self, message_ids: set, receiver_id: str, target_id: str, status: int):
        for message_id in message_ids:
            self._execute(StatementKeys.acks_insert, receiver_id, message_id, status, target_id)

    def update_acks_with_status(self, message_ids: set, receiver_id: str, status: int):
        return self._execute(StatementKeys.acks_update, status, receiver_id, message_ids)

    def msgs_select_time_slice(self, target_id: str, from_time: int, to_time: int) -> ResultSet:
        return self._execute(StatementKeys.msgs_select_time_slice, target_id, from_time, to_time)

    def msgs_select_from_user(self, from_user_id: str, limit: int=500) -> ResultSet:
        return self._execute(StatementKeys.msgs_select_from_user, from_user_id, limit)

    def msgs_select_from_user_to_target(self, from_user_id: str, target_id: str, limit: int=500) -> ResultSet:
        return self._execute(StatementKeys.msgs_select_from_user_to_target, from_user_id, target_id, limit)

    def msgs_select_from_user_to_target_time_slice(self, from_user_id: str, target_id: str, from_time: int, to_time: int, limit: int=500) -> ResultSet:
        return self._execute(StatementKeys.msgs_select_from_user_to_target_time_slice, from_user_id, target_id, from_time, to_time, limit)

    def msgs_select(self, target_id: str, limit: int=100) -> ResultSet:
        return self._execute(StatementKeys.msgs_select, target_id, limit)

    def msgs_select_all_in(self, message_ids: set) -> ResultSet:
        return self._execute(StatementKeys.msgs_select_all_in, ValueSequence(list(message_ids)))

    def msg_select(self, message_id) -> ResultSet:
        return self._execute(StatementKeys.msg_select_all, message_id)

    def msgs_select_latest_non_deleted(self, target_id: str, limit: int=100) -> ResultSet:
        return self._execute(StatementKeys.msgs_select_latest_non_deleted, target_id, limit)

    def msgs_select_since_time(self, target_id: str, time_stamp: int) -> ResultSet:
        return self._execute(StatementKeys.msgs_select_by_time_stamp, target_id, time_stamp)

    def msgs_select_non_deleted_for_user(self, from_user_id: str) -> ResultSet:
        return self._execute(StatementKeys.msg_select_msg_id_from_user_not_deleted, from_user_id)

    def msgs_select_all_for_user(self, from_user_id: str) -> ResultSet:
        return self._execute(StatementKeys.msg_select_msg_id_from_user_all, from_user_id)

    def msgs_select_non_deleted_for_user_and_time(self, from_user_id: str, from_time: int, to_time: int) -> ResultSet:
        return self._execute(
            StatementKeys.msg_select_msgs_from_user_not_deleted_for_time,
            from_user_id, from_time, to_time)

    def msgs_select_non_deleted_for_user_and_room(self, from_user_id: str, target_id: str) -> ResultSet:
        return self._execute(StatementKeys.msg_select_msg_id_from_user_and_room_not_deleted, from_user_id, target_id)

    def msg_undelete(self, message_id: str) -> None:
        self._msg_delete(message_id, deleted=False)

    def msg_delete(self, message_id: str, clear_body=True) -> None:
        self._msg_delete(message_id, deleted=True, clear_body=clear_body)

    def _msg_delete(self, message_id: str, deleted: bool, clear_body: bool=True) -> None:
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

        if len(keys.current_rows) > 1:
            logger.warning('found %s msgs when deleting with message_id %s' % (len(keys.current_rows), message_id))

        for key in keys.current_rows:
            target_id, from_user_id, timestamp = key.target_id, key.from_user_id, key.sent_time
            message_rows = self._execute(StatementKeys.msg_select_one, target_id, from_user_id, timestamp)

            if len(message_rows.current_rows) > 1:
                logger.warning(
                        'found %s msgs when deleting with target_id %s, from_user_id %s and timestamp %s' %
                        (len(message_rows.current_rows), target_id, from_user_id, timestamp))

            for message_row in message_rows.current_rows:
                logger.debug('deleting row: %s' % str(message_row))
                body = message_row.body

                if clear_body:
                    body = ''

                self.msg_update(from_user_id, target_id, body, timestamp, deleted)

    def _execute(self, statement_key, *params) -> ResultSet:
        if params is not None and len(params) > 0:
            return self.session.execute(self.statements[statement_key].bind(params))
        return self.session.execute(self.statements[statement_key])
