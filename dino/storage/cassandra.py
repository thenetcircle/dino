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

from zope.interface import implementer
from activitystreams.models.activity import Activity

from dino.storage import IStorage
from dino.config import ConfigKeys
from dino.config import AckStatus
from dino.utils import b64d
from dino.utils.decorators import timeit
from dino import environ

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


@implementer(IStorage)
class CassandraStorage(object):
    driver = None
    session = None

    def __init__(self, hosts: list, replications=None, strategy=None, key_space='dino'):
        if replications is None:
            replications = 2
        if strategy is None:
            strategy = 'SimpleStrategy'

        self.hosts = hosts
        self.key_space = key_space
        self.strategy = strategy
        self.replications = replications
        self.validate(hosts, replications, strategy)

    def init(self):
        from cassandra.cluster import Cluster
        from dino.storage.cassandra_driver import Driver
        cluster = Cluster(self.hosts)
        self.driver = Driver(cluster.connect(), self.key_space, self.strategy, self.replications)
        self.driver.init()

    @timeit(logger, 'on_message_hooks_store')
    def store_message(self, activity: Activity) -> None:
        message = b64d(activity.object.content)
        actor_name = b64d(activity.actor.display_name)
        self.driver.msg_insert(
                msg_id=activity.id,
                from_user_id=activity.actor.id,
                from_user_name=actor_name,
                target_id=activity.target.id,
                target_name=activity.target.display_name,
                body=message,
                domain=activity.target.object_type,
                sent_time=activity.published,
                channel_id=activity.object.url,
                channel_name=activity.object.display_name,
                deleted=False
        )

    def _mark_as_status(self, message_ids: set, receiver_id: str, target_id: str, status: int):
        rows = self.driver.get_acks_for(message_ids, receiver_id)

        if rows is None or len(rows.current_rows) == 0:
            current_acks = dict()
        else:
            current_acks = {row.message_id: int(row.status) for row in rows}

        to_update = list()
        to_add = list()

        for message_id in message_ids:
            if message_id not in current_acks:
                to_add.append(message_id)
                continue
                # don't downgrade status
            if current_acks.get(message_id) >= status:
                continue
            to_update.append(message_id)

        if len(to_update) > 0:
            self.driver.update_acks_with_status(message_ids, receiver_id, status)
        if len(to_add) > 0:
            self.driver.add_acks_with_status(message_ids, receiver_id, target_id, status)

    @timeit(logger, 'on_cassandra_mark_as_received')
    def mark_as_received(self, message_ids: set, receiver_id: str, target_id: str) -> None:
        self._mark_as_status(message_ids, receiver_id, target_id, AckStatus.RECEIVED)

    @timeit(logger, 'on_cassandra_mark_as_read')
    def mark_as_read(self, message_ids: set, receiver_id: str, target_id: str) -> None:
        self._mark_as_status(message_ids, receiver_id, target_id, AckStatus.READ)

    @timeit(logger, 'on_cassandra_get_messages')
    def get_messages(self, message_ids: set) -> list:
        rows = self.driver.msgs_select_all_in(message_ids)
        if rows is None or len(rows.current_rows) == 0:
            return list()
        return [self._row_to_json(row) for row in rows]

    @timeit(logger, 'on_cassandra_get_undeleted_message_ids_for_user')
    def get_undeleted_message_ids_for_user(self, user_id: str):
        rows = self.driver.msgs_select_non_deleted_for_user(user_id)
        if rows is None or len(rows.current_rows) == 0:
            return list()
        return [row.message_id for row in rows]

    @timeit(logger, 'on_cassandra_get_undeleted_message_ids_for_user_and_room')
    def get_undeleted_message_ids_for_user_and_room(self, user_id: str, room_id: str):
        rows = self.driver.msgs_select_non_deleted_for_user_and_room(user_id, room_id)
        if rows is None or len(rows.current_rows) == 0:
            return list()
        return [row.message_id for row in rows]

    @timeit(logger, 'on_cassandra_delete_message')
    def delete_message(self, message_id: str, room_id: str=None) -> None:
        self.driver.msg_delete(message_id)

    @timeit(logger, 'on_cassandra_undelete_message')
    def undelete_message(self, message_id: str) -> None:
        self.driver.msg_undelete(message_id)

    @timeit(logger, 'on_cassandra_get_unread_history')
    def get_unread_history(self, room_id: str, last_read: int) -> list:
        rows = self.driver.msgs_select_since_time(room_id, last_read)
        if rows is None or len(rows.current_rows) == 0:
            return list()

        msgs = list()
        for row in rows:
            if row.deleted:
                continue
            msgs.append(self._row_to_json(row))
        return msgs

    @timeit(logger, 'on_cassandra_get_history_for_time_slice')
    def get_history_for_time_slice(self, room_id: str, from_user_id: str, from_time: int, to_time: int) -> list:
        if room_id is not None and len(room_id.strip()) > 0:
            if from_user_id is not None and len(from_user_id.strip()) > 0:
                rows = self.driver.msgs_select_from_user_to_target_time_slice(from_user_id, room_id, from_time, to_time)
            else:
                rows = self.driver.msgs_select_time_slice(room_id, from_time, to_time)
            if rows is None or len(rows.current_rows) == 0:
                return list()
        else:
            all_rows = self.driver.msgs_select_from_user(from_user_id)
            rows = list()
            for row in all_rows:
                if row.time_stamp < from_time or row.time_stamp > to_time:
                    continue
                rows.append(row)
            if len(rows) == 0:
                return list()

        msgs = list()
        for row in rows:
            msgs.append(self._row_to_json(row))
        return msgs

    @timeit(logger, 'on_cassandra_get_history')
    def get_history(self, room_id: str, limit: int=100) -> list:
        rows = self.driver.msgs_select_latest_non_deleted(room_id, limit)
        if rows is None or len(rows.current_rows) == 0:
            return list()

        msgs = list()
        for row in rows:
            msgs.append(self._row_to_json(row))
        return msgs

    @timeit(logger, 'on_cassandra_msg_select')
    def msg_select(self, message_id: str) -> dict:
        rows = self.driver.msg_select(message_id)
        if rows is None or len(rows.current_rows) == 0:
            return dict()
        if len(rows.current_rows) > 1:
            logger.warning('multiple messages found for id %s' % message_id)
        for row in rows:
            # only interested in the first one if multiple
            return self._row_to_json(row)

    def _row_to_json(self, row):
        return {
            'message_id': row.message_id,
            'from_user_id': row.from_user_id,
            'from_user_name': row.from_user_name,
            'target_id': row.target_id,
            'target_name': row.target_name,
            'body': row.body,
            'domain': row.domain,
            'channel_id': row.channel_id,
            'channel_name': row.channel_name,
            'timestamp': row.sent_time,
            'deleted': row.deleted
        }

    def validate(self, hosts, replications, strategy):
        if environ.env.config.get(ConfigKeys.TESTING, False):
            return

        if not isinstance(replications, int):
            raise ValueError('replications is not a valid int: "%s"' % str(replications))
        if replications < 1 or replications > 99:
            raise ValueError('replications needs to be in the interval [1, 99]')

        if replications > len(hosts):
            logger.warning('replications (%s) is higher than number of nodes in cluster (%s)' %
                             (str(replications), len(hosts)))

        if not isinstance(strategy, str):
            raise ValueError('strategy is not a valid string, but of type: "%s"' % str(type(strategy)))

        valid_strategies = ['SimpleStrategy', 'NetworkTopologyStrategy']
        if strategy not in valid_strategies:
            raise ValueError('unknown strategy "%s", valid strategies are: %s' %
                             (str(strategy), ', '.join(valid_strategies)))
