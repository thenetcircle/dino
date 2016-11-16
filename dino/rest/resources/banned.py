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

from functools import lru_cache
from datetime import datetime

from dino.rest.resources.base import BaseResource
from dino import environ

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class BannedResource(BaseResource):
    def __init__(self):
        super(BannedResource, self).__init__()
        self.last_cleared = datetime.utcnow()

    def _get_lru_method(self):
        return self.do_get

    def _get_last_cleared(self):
        return self.last_cleared

    def _set_last_cleared(self, last_cleared):
        self.last_cleared = last_cleared

    @lru_cache()
    def do_get(self):
        return environ.env.db.get_banned_users()
