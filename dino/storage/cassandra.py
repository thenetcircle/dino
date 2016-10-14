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

from dino.storage.base import IStorage
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

    def delete_acl(self, room_id: str, acl_type: str) -> None:
        current_acls = self.get_acls(room_id)

        if acl_type in current_acls:
            del current_acls[acl_type]
            self.driver.acl_insert(room_id, current_acls)

    def add_acls(self, room_id: str, acls: dict) -> None:
        current_acls = self.get_acls(room_id)

        for acl_type, acl_value in acls.items():
            current_acls[acl_type] = acl_value

        self.driver.acl_insert(room_id, current_acls)

    def get_acls(self, room_id: str) -> dict:
        rows = self.driver.acl_select(room_id)
        if rows is None or len(rows.current_rows) == 0:
            return dict()

        acls = dict()
        for row in rows:
            if row.age is not None:
                acls[SessionKeys.age.value] = row.age
            if row.gender is not None:
                acls[SessionKeys.gender.value] = row.gender
            if row.membership is not None:
                acls[SessionKeys.membership.value] = row.membership
            if row.group is not None:
                acls[SessionKeys.group.value] = row.group
            if row.country is not None:
                acls[SessionKeys.country.value] = row.country
            if row.city is not None:
                acls[SessionKeys.city.value] = row.city
            if row.image is not None:
                acls[SessionKeys.image.value] = row.image
            if row.has_webcam is not None:
                acls[SessionKeys.has_webcam.value] = row.has_webcam
            if row.fake_checked is not None:
                acls[SessionKeys.fake_checked.value] = row.fake_checked
            break

        return acls

    def set_user_offline(self, user_id: str) -> None:
        # TODO
        pass

    def set_user_online(self, user_id: str) -> None:
        # TODO
        pass

    def set_user_invisible(self, user_id: str) -> None:
        # TODO
        pass

    def remove_current_rooms_for_user(self, user_id: str) -> None:
        rows = self.driver.rooms_select_for_user(user_id)
        if rows is None or len(rows.current_rows) == 0:
            return

        for row in rows:
            self.leave_room(user_id, row.room_id)

    def room_exists(self, room_id: str) -> bool:
        rows = self.driver.room_select_name(room_id)
        return rows is not None and len(rows.current_rows) > 0

    def room_name_exists(self, room_name: str) -> bool:
        rows = self.driver.rooms_select()
        if rows is None or len(rows.current_rows) == 0:
            return False

        names = set()
        for row in rows:
            names.add(row.room_name)

        return room_name in names

    def room_contains(self, room_id: str, user_id: str) -> bool:
        rows = self.driver.room_select_users(room_id)
        if rows is None or len(rows.current_rows) == 0:
            return False

        for row in rows:
            if row.user_id == user_id:
                return True
        return False

    def store_message(self, activity: Activity) -> None:
        self.driver.msg_insert(
            activity.id,
            activity.actor.id,
            activity.target.id,
            activity.object.content,
            activity.target.object_type,
            activity.published
        )

    def create_room(self, activity: Activity) -> None:
        self.driver.room_insert(
            activity.target.id,
            activity.target.display_name,
            [activity.actor.id],
            activity.published
        )

    def get_history(self, room_id: str, limit: int=None) -> list:
        # TODO: limit
        rows = self.driver.msgs_select(room_id)
        if rows is None or len(rows.current_rows) == 0:
            return list()

        msgs = list()
        for row in rows:
            msgs.append({
                'message_id': row.message_id,
                'from_user': row.from_user,
                'to_user': row.to_user,
                'body': row.body,
                'domain': row.domain,
                'timestamp': row.time
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

    def get_all_rooms(self, user_id: str=None) -> list:
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
                'created': row.time,
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
