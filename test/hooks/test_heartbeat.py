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

from unittest.mock import MagicMock
from activitystreams import parse as as_parser

from test.base import BaseTest
from dino import environ
from dino.config import RedisKeys
from dino.config import UserKeys
from dino.hooks.heartbeat import OnHeartbeatHooks


class MockHeartbeatManager(object):
    def __init__(self):
        self._ids = set()

    def has_heartbeat(self, user_id: str) -> bool:
        return user_id in self._ids

    def add_heartbeat(self, user_id: str) -> None:
        self._ids.add(user_id)


class HeartbeatHooksTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.published = []
        environ.env.heartbeat = MockHeartbeatManager()
        environ.env.publish = self._capture_publish
        environ.env.cache = MagicMock()
        environ.env.cache.check_heartbeat = MagicMock()
        environ.env.cache.set_user_invisible = MagicMock()
        environ.env.cache.get_user_status = MagicMock(return_value=None)
        environ.env.db.set_user_online = MagicMock()

    def _capture_publish(self, activity, **kwargs):
        self.published.append((activity, kwargs))

    def _activity(self):
        data = {
            'actor': {
                'id': BaseTest.USER_ID,
                'displayName': BaseTest.USER_NAME,
            },
            'verb': 'heartbeat',
        }
        return data, as_parser(data)

    def test_invisible_heartbeat_does_not_update_last_online(self):
        environ.env.redis.set(RedisKeys.user_status(BaseTest.USER_ID), UserKeys.STATUS_INVISIBLE)
        OnHeartbeatHooks.set_user_online_if_not_previously_invisible(self._activity())
        environ.env.cache.set_user_invisible.assert_called_once_with(
            BaseTest.USER_ID, update_last_online=False)
        environ.env.db.set_user_online.assert_not_called()

    def test_visible_heartbeat_sets_online(self):
        OnHeartbeatHooks.set_user_online_if_not_previously_invisible(self._activity())
        environ.env.db.set_user_online.assert_called_once_with(BaseTest.USER_ID)
        environ.env.cache.set_user_invisible.assert_not_called()

    def test_first_heartbeat_login_event_uses_invisible_status(self):
        environ.env.redis.set(RedisKeys.user_status(BaseTest.USER_ID), UserKeys.STATUS_INVISIBLE)
        # first heartbeat: manager does not yet know this user
        OnHeartbeatHooks.publish_activity(self._activity())
        self.assertEqual(1, len(self.published))
        activity, _ = self.published[0]
        self.assertEqual('invisible', activity['actor']['summary'])
        self.assertEqual('login', activity['verb'])
