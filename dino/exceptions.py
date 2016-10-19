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

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class NoSuchChannelException(Exception):
    def __init__(self, uuid):
        self.uuid = uuid


class RoomExistsException(Exception):
    def __init__(self, uuid):
        self.uuid = uuid


class ChannelExistsException(Exception):
    def __init__(self, uuid):
        self.uuid = uuid


class NoSuchRoomException(Exception):
    def __init__(self, uuid):
        self.uuid = uuid


class NoSuchUserException(Exception):
    def __init__(self, uuid):
        self.uuid = uuid


class UserExistsException(Exception):
    def __init__(self, uuid):
        self.uuid = uuid


class RoomNameExistsForChannelException(Exception):
    def __init__(self, channel_uuid, room_name):
        self.channel_uuid = channel_uuid
        self.room_name = room_name
