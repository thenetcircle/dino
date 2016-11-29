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


class UnknownBanTypeException(Exception):
    def __init__(self, ban_type):
        self.ban_type = ban_type


class NoSuchChannelException(Exception):
    def __init__(self, uuid):
        self.uuid = uuid


class EmptyRoomNameException(Exception):
    def __init__(self, uuid):
        self.uuid = uuid


class EmptyUserNameException(Exception):
    def __init__(self, uuid):
        self.uuid = uuid


class EmptyUserIdException(Exception):
    pass


class EmptyChannelNameException(Exception):
    def __init__(self, uuid):
        self.uuid = uuid


class RoomExistsException(Exception):
    def __init__(self, uuid):
        self.uuid = uuid


class NoChannelFoundException(Exception):
    def __init__(self, room_uuid):
        self.room_uuid = room_uuid


class ChannelExistsException(Exception):
    def __init__(self, uuid):
        self.uuid = uuid


class NoRoomNameException(Exception):
    def __init__(self, uuid):
        self.uuid = uuid


class NoSuchRoomException(Exception):
    def __init__(self, uuid):
        self.uuid = uuid


class InvalidAclTypeException(Exception):
    def __init__(self, acl_type):
        self.acl_type = acl_type


class InvalidAclValueException(Exception):
    def __init__(self, acl_type, acl_value):
        self.acl_type = acl_type
        self.acl_value = acl_value


class InvalidApiActionException(Exception):
    def __init__(self, action):
        self.action = action


class AclValueNotFoundException(Exception):
    def __init__(self, acl_type: str, validation_method: str):
        self.acl_type = acl_type
        self.validation_method = validation_method


class NoSuchUserException(Exception):
    def __init__(self, uuid):
        self.uuid = uuid


class ValidationException(Exception):
    def __init__(self, msg):
        self.msg = msg


class UserExistsException(Exception):
    def __init__(self, uuid):
        self.uuid = uuid


class NoOriginChannelException(Exception):
    pass


class NoTargetChannelException(Exception):
    pass


class NoOriginRoomException(Exception):
    pass


class NoTargetRoomException(Exception):
    pass


class RoomNameExistsForChannelException(Exception):
    def __init__(self, channel_uuid, room_name):
        self.channel_uuid = channel_uuid
        self.room_name = room_name


class ChannelNameExistsException(Exception):
    def __init__(self, channel_name):
        self.channel_name = channel_name
