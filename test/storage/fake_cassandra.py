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
from datetime import datetime

from dino.storage.cassandra_driver import IDriver
from dino.config import ConfigKeys

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
        self.msgs_to_user = dict()

    def init(self):
        pass

    def msg_insert(self, msg_id, from_user, to_user, body, domain, sent_time, channel_id, deleted=False) -> None:
        if to_user not in self.msgs_to_user:
            self.msgs_to_user[to_user] = list()
        time_stamp = int(datetime.strptime(sent_time, ConfigKeys.DEFAULT_DATE_FORMAT).strftime('%s'))
        self.msgs_to_user[to_user].append((msg_id, from_user, to_user, body, domain, sent_time, time_stamp, channel_id, deleted))

    def msgs_select(self, to_user_id: str, limit: int=100) -> ResultSet:
        msgs = self.msgs_to_user.get(to_user_id, list())[:limit]
        rows = list()
        for msg_id, from_user, to_user, body, domain, sent_time, time_stamp, channel_id, deleted in msgs:
            row = FakeResultSet.FakeRow()
            row.message_id = msg_id
            row.from_user = from_user
            row.to_user = to_user
            row.body = body
            row.domain = domain
            row.time_stamp = time_stamp
            row.sent_time = sent_time
            row.channel_id = channel_id
            row.deleted = deleted
            rows.append(row)
        return FakeResultSet(rows)

    def msgs_select_since_time(self, to_user_id: str, time_stamp: int) -> ResultSet:
        msgs = self.msgs_select(to_user_id, 999999)
        filtered = list()
        for msg in msgs:
            if msg.time_stamp < time_stamp:
                continue
            filtered.append(msg)
        return FakeResultSet(filtered)

    def msg_delete(self, message_id: str) -> ResultSet:
        found = False
        for room_id, msgs in self.msgs_to_user.items():
            new_msgs = list()
            for msg_id, from_user, to_user, body, domain, sent_time, time_stamp, channel_id, deleted in msgs:
                if msg_id == message_id:
                    found = True
                    continue
                new_msgs.append((msg_id, from_user, to_user, body, domain, sent_time, time_stamp, channel_id, deleted))

            if found:
                self.msgs_to_user[room_id] = new_msgs
                break
