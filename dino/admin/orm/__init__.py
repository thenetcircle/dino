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

from dino.db.manager import ChannelManager
from dino.db.manager import RoomManager
from dino.db.manager import UserManager
from dino.db.manager import AclManager
from dino.db.manager import StorageManager
from dino.db.manager import BlackListManager
from dino.environ import env

channel_manager = ChannelManager(env)
room_manager = RoomManager(env)
user_manager = UserManager(env)
storage_manager = StorageManager(env)
acl_manager = AclManager(env)
blacklist_manager = BlackListManager(env)
