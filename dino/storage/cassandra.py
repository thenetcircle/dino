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
from dino.utils import b64d
from dino import environ

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


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
        self.logger = logging.getLogger(__name__)
        self.validate(hosts, replications, strategy)

    def init(self):
        from cassandra.cluster import Cluster
        from dino.storage.cassandra_driver import Driver
        cluster = Cluster(self.hosts)
        self.driver = Driver(cluster.connect(), self.key_space, self.strategy, self.replications)
        self.driver.init()

    def store_message(self, activity: Activity) -> None:
        message = b64d(activity.object.content)
        self.driver.msg_insert(
                msg_id=activity.id,
                from_user_id=activity.actor.id,
                from_user_name=activity.actor.summary,
                target_id=activity.target.id,
                target_name=activity.target.display_name,
                body=message,
                domain=activity.target.object_type,
                sent_time=activity.published,
                channel_id=activity.object.url,
                channel_name=activity.object.summary,
                deleted=False
        )

    def delete_message(self, room_id: str, message_id: str):
        self.driver.msg_delete(message_id)

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

    def get_history(self, room_id: str, limit: int=100) -> list:
        rows = self.driver.msgs_select(room_id, limit)
        if rows is None or len(rows.current_rows) == 0:
            return list()

        msgs = list()
        for row in rows:
            if row.deleted:
                continue
            msgs.append(self._row_to_json(row))
        return msgs

    def _row_to_json(self, row):
        return {
            'message_id': row.message_id,
            'from_user_id': row.from_user_id,
            'from_user_name': row.from_user_id,
            'target_id': row.target_id,
            'target_name': row.taret_name,
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
            self.logger.warn('replications (%s) is higher than number of nodes in cluster (%s)' %
                             (str(replications), len(hosts)))

        if not isinstance(strategy, str):
            raise ValueError('strategy is not a valid string, but of type: "%s"' % str(type(strategy)))

        valid_strategies = ['SimpleStrategy', 'NetworkTopologyStrategy']
        if strategy not in valid_strategies:
            raise ValueError('unknown strategy "%s", valid strategies are: %s' %
                             (str(strategy), ', '.join(valid_strategies)))
