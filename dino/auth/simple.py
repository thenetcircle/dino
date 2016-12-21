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
from typing import Union

from dino.auth import IAuth

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


@implementer(IAuth)
class AllowAllAuth(object):
    def __init__(self):
        pass

    def get_user_info(self, user_id: str) -> dict:
        return dict()

    def authenticate_and_populate_session(self, user_id: str, token: str) -> (bool, Union[None, str], Union[None, dict]):
        return True, None, {'user_id': user_id, 'token': token}


@implementer(IAuth)
class DenyAllAuth(object):
    def __init__(self):
        pass

    def get_user_info(self, user_id: str) -> dict:
        return dict()

    def authenticate_and_populate_session(self, user_id: str, token: str) -> (bool, Union[None, str], Union[None, dict]):
        return False, 'not allowed', None
