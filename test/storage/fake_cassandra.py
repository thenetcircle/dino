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
from cassandra.cluster import ResultSet

from dino.storage.cassandra_driver import IDriver

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class FakeResultSet(object):
    class FakeRow(object):
        def __init__(self):
            self.__dict__['vals'] = dict()

        def __setattr__(self, key, value):
            self.vals[key] = value

        def __getattr__(self, item):
            if item not in self.__dict__['vals']:
                return None
            return self.__dict__['vals'][item]

    def __init__(self, current_rows):
        if isinstance(current_rows, dict):
            self.current_rows = list()
            row = FakeResultSet.FakeRow()
            for rkey, rval in current_rows.items():
                row.__setattr__(rkey, rval)
            self.current_rows.append(row)
        else:
            self.current_rows = current_rows

    def __iter__(self):
        for row in self.current_rows:
            yield row


@implementer(IDriver)
class FakeCassandraDriver(object):
    def __init__(self):
        self.acls = dict()
        self.owners = dict()
        self.room_names = dict()
        self.rooms = dict()
        self.rooms_for_user = dict()
        self.users_in_room = dict()
        self.msgs_to_user = dict()

    def init(self):
        pass

    def acl_insert(self, room_id: str, acls: dict) -> None:
        acl = dict()
        for akey, aval in acls.items():
            acl[akey] = aval
        self.acls[room_id] = acl

    def acl_select(self, room_id: str) -> ResultSet:
        if room_id not in self.acls:
            return FakeResultSet([])

        acls = self.acls[room_id]
        rows = list()
        row = FakeResultSet.FakeRow()
        for acl_key, acl_val in acls.items():
            row.__setattr__(acl_key, acl_val)
        rows.append(row)
        return FakeResultSet(rows)

    def msg_insert(self, msg_id, from_user, to_user, body, domain, timestamp) -> None:
        if to_user not in self.msgs_to_user:
            self.msgs_to_user[to_user] = list()
        self.msgs_to_user[to_user].append((msg_id, from_user, to_user, body, domain, timestamp))

    def room_insert(self, room_id: str, room_name: str, owners: list, timestamp: str) -> None:
        self.rooms[room_id] = (room_id, room_name, owners, timestamp)
        self.room_names[room_id] = room_name
        self.owners[room_id] = owners

    def msgs_select(self, to_user_id: str) -> ResultSet:
        msgs = self.msgs_to_user.get(to_user_id, list())
        rows = list()
        for msg_id, from_user, to_user, body, domain, timestamp in msgs:
            row = FakeResultSet.FakeRow()
            row.message_id = msg_id
            row.from_user = from_user
            row.to_user = to_user
            row.body = body
            row.domain = domain
            row.timestamp = timestamp
            rows.append(row)
        return FakeResultSet(rows)

    def rooms_select(self) -> ResultSet:
        rows = list()
        for _, (room_id, room_name, owners, timestamp) in self.rooms.items():
            row = FakeResultSet.FakeRow()
            row.room_id = room_id
            row.room_name = room_name
            row.owners = owners
            row.timestamp = timestamp
            rows.append(row)
        return FakeResultSet(rows)

    def room_select_name(self, room_id: str) -> ResultSet:
        if room_id not in self.room_names:
            return FakeResultSet([])
        row = FakeResultSet.FakeRow()
        row.room_name = self.room_names[room_id]
        return FakeResultSet([row])

    def room_select_users(self, room_id: str) -> ResultSet:
        users = self.users_in_room.get(room_id, dict())
        rows = list()
        for user_id, user_name in users.items():
            row = FakeResultSet.FakeRow()
            row.user_id = user_id
            row.user_name = user_name
            rows.append(row)
        return FakeResultSet(rows)

    def room_select_owners(self, room_id: str) -> ResultSet:
        if room_id not in self.owners:
            row = FakeResultSet.FakeRow()
            row.owners = []
            return FakeResultSet([row])

        row = FakeResultSet.FakeRow()
        row.owners = self.owners[room_id]
        return FakeResultSet([row])

    def rooms_select_for_user(self, user_id: str) -> ResultSet:
        rooms = self.rooms_for_user.get(user_id, list())
        rows = list()

        for room_id, room_name, *rest in rooms:
            row = FakeResultSet.FakeRow()
            row.room_id = room_id
            row.room_name = room_name
            rows.append(row)
        return FakeResultSet(rows)

    def room_insert_user(self, room_id: str, room_name: str, user_id: str, user_name: str) -> None:
        if user_id not in self.rooms_for_user:
            self.rooms_for_user[user_id] = list()
        if room_id not in self.users_in_room:
            self.users_in_room[room_id] = dict()
        self.rooms_for_user[user_id].append((room_id, room_name, user_id, user_name))
        self.users_in_room[room_id][user_id] = user_name

    def room_delete_user(self, room_id: str, user_id: str) -> None:
        if user_id in self.rooms_for_user:
            del self.rooms_for_user[user_id]
        if room_id in self.users_in_room and user_id in self.users_in_room[room_id]:
            del self.users_in_room[room_id][user_id]
