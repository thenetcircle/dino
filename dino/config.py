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

from enum import Enum

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


# TODO: session keys should be configurable, and config should also contain whether or not they're required
class SessionKeys(Enum):
    user_id = 'user_id'
    user_name = 'user_name'
    age = 'age'
    gender = 'gender'
    membership = 'membership'
    group = 'group'
    country = 'country'
    city = 'city'
    image = 'image'
    has_webcam = 'has_webcam'
    fake_checked = 'fake_checked'
    token = 'token'

    requires_session_keys = {
        user_id,
        user_name,
        age,
        gender,
        membership,
        country,
        city,
        image,
        has_webcam,
        fake_checked,
        token
    }


class ConfigKeys(object):
    LOG_LEVEL = 'log_level'
    LOG_FORMAT = 'log_format'
    DEBUG = 'debug'
    QUEUE = 'queue'
    TESTING = 'testing'
    STORAGE = 'storage'
    AUTH_SERVICE = 'auth'
    HOST = 'host'
    TYPE = 'type'
    MAX_HISTORY = 'max_history'
    STRATEGY = 'strategy'
    REPLICATION = 'replication'
    REDIS_AUTH_KEY = 'redis_key'
    DB = 'db'

    # will be overwritten even if specified in config file
    ENVIRONMENT = '_environment'
    VERSION = '_version'
    LOGGER = '_logger'
    REDIS = '_redis'
    SESSION = '_session'

    DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)-18s - %(levelname)-7s - %(message)s"
    DEFAULT_LOG_LEVEL = 'INFO'
    DEFAULT_REDIS_HOST = 'localhost'
