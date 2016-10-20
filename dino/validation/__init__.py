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

from activitystreams.models.activity import Activity

from dino.validation.request_validator import RequestValidator
from dino import environ

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

request = RequestValidator()


class BaseValidator(object):
    def validate_request(self, activity: Activity) -> (bool, str):
        if not hasattr(activity.actor, 'id') or activity.actor.id is None:
            return False, 'no ID on actor'

        session_user_id = environ.env.session.get('user_id', 'NOT_FOUND_IN_SESSION')
        if activity.actor.id != session_user_id:
            error_msg = "user_id in session '%s' doesn't match user_id in request '%s'"
            return False, error_msg % (session_user_id, activity.actor.id)

        return True, None
