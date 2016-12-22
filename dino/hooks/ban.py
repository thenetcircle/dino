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

import logging

from dino import environ
from dino import utils

logger = logging.getLogger(__name__)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class OnBanHooks(object):
    @staticmethod
    def publish_activity(arg: tuple) -> None:
        data, activity = arg
        print('hook publish to nodes')
        from pprint import pprint
        pprint(data)
        environ.env.publish(data)


@environ.env.observer.on('on_ban')
def _on_ban_ban_user(arg: tuple) -> None:
    OnBanHooks.publish_activity(arg)
