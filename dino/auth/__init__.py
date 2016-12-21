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

from zope.interface import Interface
from typing import Union

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class IAuth(Interface):
    def authenticate_and_populate_session(self, user_id: str, token: str) -> (bool, Union[None, str], Union[None, dict]):
        """
        authenticates a user with a token

        :param user_id: the user id
        :param token: the token for the login
        :return: if success: (True, None, <dict with session values>), if failure: (False, <error string>, None)
        """

    def get_user_info(self, user_id: str) -> dict:
        """
        get the information about a user stored for validation purposes for acls, e.g. age, gender etc.

        token, user_id and user_name will be skipped (if present)

        :param user_id: the id of the user
        :return: a dict with user info
        """
