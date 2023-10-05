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

from unittest import TestCase
from activitystreams.models.activity import Activity
from zope.interface import implementer

from dino.utils.decorators import pre_process
from dino.utils.decorators import count_connections
from dino.utils.decorators import respond_with
from dino.stats import IStats
from dino.environ import ConfigDict
from dino.config import SessionKeys
from dino.config import ErrorCodes
from dino import environ

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


@implementer(IStats)
class FakeStats(object):
    def __init__(self):
        self.count = 0

    def incr(self, key):
        self.count += 1

    def decr(self, key):
        self.count -= 1

    def gauge(self, key, val):
        pass

    def timing(self, key, val):
        pass


class DecoratorTest(TestCase):
    emit_args = None

    @staticmethod
    def _emit(*args, **kwargs):
        DecoratorTest.emit_args = args

    def setUp(self):
        environ.env.config = ConfigDict({})
        environ.env.stats = FakeStats()
        environ.env.emit = DecoratorTest._emit
        environ.env.session = {
            SessionKeys.user_id.value: '1234',
            SessionKeys.user_name.value: 'batman'
        }
        DecoratorTest.emit_args = None
        self.env = environ.env

    def test_pre_process(self):
        @pre_process('on_test')
        def to_decorate(data: dict, activity: Activity=None):
            self.assertIsNotNone(activity)
            self.assertIsNotNone(activity.id)
            self.assertIsNotNone(activity.published)
            return 200, None
        status, msg, *rest = to_decorate(self.get_activity())
        self.assertEqual(200, status)

    def test_pre_process_exception(self):
        @pre_process('on_test')
        def to_decorate(data: dict, activity: Activity=None):
            raise RuntimeError('testing')
        status, msg, *rest = to_decorate(self.get_activity())
        self.assertEqual(ErrorCodes.UNKNOWN_ERROR, status)

    def test_invalid_name(self):
        @pre_process('does-not-exist')
        def to_decorate(data: dict, activity: Activity=None):
            pass
        self.assertRaises(RuntimeError, to_decorate, self.get_activity())

    def test_count_connections(self):
        @count_connections('connect')
        def login(): pass

        @count_connections('disconnect')
        def logout(): pass

        self.assertEqual(0, environ.env.stats.count)
        login()
        self.assertEqual(1, environ.env.stats.count)
        login()
        self.assertEqual(2, environ.env.stats.count)
        logout()
        self.assertEqual(1, environ.env.stats.count)

    def test_respond_with(self):
        @respond_with('gn_test')
        def foo(data: dict, activity: Activity=None):
            return 200, 'ok'

        self.assertIsNone(DecoratorTest.emit_args)
        response = foo(self.get_activity())
        self.assertEqual(200, response.get('status_code'))
        self.assertIsNone(response.get('message'))
        self.assertIsNotNone(response.get('data'))
        self.assertEqual(DecoratorTest.emit_args, ('gn_test', {'status_code': 200, 'data': 'ok'}))

    def test_respond_with_exception(self):
        @respond_with('gn_test')
        def foo(data: dict, activity: Activity=None): raise RuntimeError('testing')

        self.assertIsNone(DecoratorTest.emit_args)
        response, msg = foo(self.get_activity())
        self.assertEqual(response, 500)
        self.assertIsNotNone(msg)

    def get_activity(self):
        return {
            'actor': {
                'id': '1234'
            },
            'verb': 'test'
        }
