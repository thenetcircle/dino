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

from cassandra.cluster import ResultSet
from cassandra.cluster import Session
from enum import Enum
from zope.interface import Interface
from zope.interface import implementer

from dino import environ
from dino.config import SessionKeys

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class StatementKeys(Enum):
    msg_insert = 'msg_insert'
    msg_select = 'msg_select'
    msgs_select = 'msgs_select'
    msg_select_one = 'msg_select_one'


class IDriver(Interface):
    def init(self):
        """
        creates keyspace, tables, views etc.

        :return: nothing
        """

    def msg_select(self, msg_id) -> ResultSet:
        """
        select one message

        :param msg_id: uuid of the message
        :return: the message, if found
        """

    def msg_insert(self, msg_id, from_user, to_user, body, domain, timestamp, channel_id, deleted=False) -> None:
        """
        store a new message

        :param msg_id: uuid of the message
        :param from_user: id of the user sending the message
        :param to_user: id of the user receiving the message (or uuid of the target room)
        :param body: the message text
        :param domain: private/group
        :param timestamp: published timestamp
        :param channel_id: the channel of the room
        :param deleted: if the message is deleted or not
        :return: nothing
        """

    def msgs_select(self, to_user_id: str) -> ResultSet:
        """
        find all messages sent to a user id/room id

        :param to_user_id: either a user id or room uuid
        :return: all messages to this user/room
        """


@implementer(IDriver)
class Driver(object):
    def __init__(self, session: Session, key_space: str, strategy: str, replications: int):
        self.session = session
        self.statements = dict()
        self.key_space = key_space
        self.strategy = strategy
        self.replications = replications

    def init(self):
        def create_key_space():
            environ.env.logger.debug('creating keyspace...')
            create_key_space_stmt = self.session.prepare(
                    """
                    CREATE KEYSPACE IF NOT EXISTS %s
                    WITH replication = {'class': '%s', 'replication_factor': '%s'}
                    """ % (self.key_space, self.strategy, str(self.replications))
            )
            self.session.execute(create_key_space_stmt)
            self.session.set_keyspace(self.key_space)

        def create_tables():
            environ.env.logger.debug('creating tables...')
            self.session.execute(
                    """
                    CREATE TABLE IF NOT EXISTS messages (
                        message_id varchar,
                        from_user text,
                        to_user text,
                        body text,
                        domain text,
                        sent_time varchar,
                        channel_id varchar,
                        deleted boolean,
                        PRIMARY KEY (to_user, from_user, sent_time)
                    )
                    """
            )

        def create_views():
            self.session.execute(
                    """
                    CREATE MATERIALIZED VIEW IF NOT EXISTS messages_by_id AS
                        SELECT message_id, to_user, from_user, sent_time from messages
                            WHERE
                                message_id IS NOT NULL AND
                                to_user IS NOT NULL AND
                                from_user IS NOT NULL AND
                                sent_time IS NOT NULL
                        PRIMARY KEY (message_id, to_user, from_user, sent_time)
                        WITH comment='allows lookups of to_user and from_user by message_id'
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
                        sent_time,
                        channel_id,
                        deleted
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """
            )
            self.statements[StatementKeys.msgs_select] = self.session.prepare(
                    """
                    SELECT * FROM messages WHERE to_user = ?
                    """
            )
            self.statements[StatementKeys.msg_select] = self.session.prepare(
                    """
                    SELECT to_user, from_user, sent_time FROM messages_by_id WHERE message_id = ?
                    """
            )
            self.statements[StatementKeys.msg_select_one] = self.session.prepare(
                    """
                    SELECT * FROM messages WHERE to_user = ? AND from_user = ? AND sent_time = ?
                    """
            )

        create_key_space()
        create_tables()
        create_views()
        prepare_statements()

    def msg_insert(self, msg_id, from_user, to_user, body, domain, timestamp, channel_id, deleted=False) -> None:
        self._execute(
                StatementKeys.msg_insert, msg_id, from_user, to_user,
                body, domain, timestamp, channel_id, deleted)

    def msgs_select(self, to_user_id: str) -> ResultSet:
        return self._execute(StatementKeys.msgs_select, to_user_id)

    def msg_delete(self, message_id: str) -> ResultSet:
        """
        We're doing three queries here, one to get primary index of messages table from message_id, then getting the
        complete row from messages table, and finally updating that row. This could be lowered to two queries by
        duplicating everything from messages table to messages_by_id materialized view, but would also double storage
        requirements. Since message deletion is likely not a frequent operation we can accept doing three queries.
        """
        keys = self._execute(StatementKeys.msg_select, message_id)
        if keys is None or len(keys.current_rows) == 0:
            # not found
            return

        assert len(keys.current_rows) == 1
        key = keys.current_rows[0]
        to_user, from_user, timestamp = key.to_user, key.from_user, key.sent_time

        message_rows = self._execute(StatementKeys.msg_select_one, to_user, from_user, timestamp)
        assert len(message_rows.current_rows) == 1

        message_row = message_rows.current_rows[0]
        body = message_row.body
        domain = message_row.domain
        channel_id = message_row.channel_id
        self.msg_insert(message_id, from_user, to_user, body, domain, timestamp, channel_id, deleted=True)

    def _execute(self, statement_key, *params) -> ResultSet:
        if params is not None and len(params) > 0:
            return self.session.execute(self.statements[statement_key].bind(params))
        return self.session.execute(self.statements[statement_key])
