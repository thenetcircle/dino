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

from zope.interface import implementer
from activitystreams.models.activity import Activity
from cassandra.cluster import Cluster

from dino.storage import IStorage
from dino import environ
from dino.storage.cassandra_driver import Driver
from dino.config import SessionKeys
from dino.config import ConfigKeys

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

        CassandraStorage.validate(hosts, replications, strategy)

    def init(self):
        cluster = Cluster(self.hosts)
        self.driver = Driver(cluster.connect(), self.key_space, self.strategy, self.replications)
        self.driver.init()

    def store_message(self, activity: Activity) -> None:
        self.driver.msg_insert(
                msg_id=activity.id,
                from_user=activity.actor.id,
                to_user=activity.target.id,
                body=activity.object.content,
                domain=activity.target.object_type,
                timestamp=activity.published,
                channel_id=activity.object.url,
                deleted=False
        )

    def delete_message(self, room_id: str, message_id: str):
        self.driver.msg_delete(message_id)

    def create_room(self, activity: Activity) -> None:
        self.driver.room_insert(
                activity.target.id,
                activity.target.display_name,
                [activity.actor.id],
                activity.published
        )

    def get_history(self, room_id: str, limit: int = None) -> list:
        # TODO: limit
        rows = self.driver.msgs_select(room_id)
        if rows is None or len(rows.current_rows) == 0:
            return list()

        msgs = list()
        for row in rows:
            if row.deleted:
                continue

            msgs.append({
                'message_id': row.message_id,
                'from_user': row.from_user,
                'to_user': row.to_user,
                'body': row.body,
                'domain': row.domain,
                'channel_id': row.channel_id,
                'timestamp': row.sent_time
            })
        return msgs

    def get_room_name(self, room_id: str) -> str:
        results = self.driver.room_select_name(room_id)
        current_rows = results.current_rows
        if len(current_rows) == 0:
            return ''
        row = current_rows[0]
        return row.room_name

    def join_room(self, user_id: str, user_name: str, room_id: str, room_name: str) -> None:
        self.driver.room_insert_user(room_id, room_name, user_id, user_name)

    def users_in_room(self, room_id: str) -> list:
        rows = self.driver.room_select_users(room_id)
        if rows is None or len(rows.current_rows) == 0:
            return list()

        users = list()
        for row in rows:
            users.append({
                'user_id': row.user_id,
                'user_name': row.user_name
            })
        return users

    def get_all_rooms(self, user_id: str = None) -> list:
        if user_id is None:
            rows = self.driver.rooms_select()
        else:
            rows = self.driver.rooms_select_for_user(user_id)

        if rows is None or len(rows.current_rows) == 0:
            return list()

        rooms = list()
        for row in rows:
            rooms.append({
                'room_id': row.room_id,
                'room_name': row.room_name,
                'created': row.creation_time,
                'owners': row.owners
            })
        return rooms

    def leave_room(self, user_id: str, room_id: str) -> None:
        self.driver.room_delete_user(room_id, user_id)

    def get_owners(self, room_id: str) -> list:
        rows = self.driver.room_select_owners(room_id)
        if rows is None or len(rows.current_rows) == 0 or \
                (len(rows.current_rows) == 1 and len(rows.current_rows[0].owners) == 0):
            return list()

        owner_rows = rows.current_rows[0].owners
        owners = list()
        for owner in owner_rows:
            owners.append({
                'user_id': owner
            })
        return owners

    def room_owners_contain(self, room_id: str, user_id: str) -> bool:
        owners = self.get_owners(room_id)
        for owner in owners:
            if owner['user_id'] == user_id:
                return True
        return False

    @staticmethod
    def validate(hosts, replications, strategy):
        if environ.env.config.get(ConfigKeys.TESTING, False):
            return

        if not isinstance(replications, int):
            raise ValueError('replications is not a valid int: "%s"' % str(replications))
        if replications < 1 or replications > 99:
            raise ValueError('replications needs to be in the interval [1, 99]')

        if replications > len(hosts):
            environ.env.logger.warn('replications (%s) is higher than number of nodes in cluster (%s)' %
                                    (str(replications), len(hosts)))

        if not isinstance(strategy, str):
            raise ValueError('strategy is not a valid string, but of type: "%s"' % str(type(strategy)))

        valid_strategies = ['SimpleStrategy', 'NetworkTopologyStrategy']
        if strategy not in valid_strategies:
            raise ValueError('unknown strategy "%s", valid strategies are: %s' %
                             (str(strategy), ', '.join(valid_strategies)))
