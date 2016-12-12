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
    def ban_user(arg: tuple) -> None:
        data, activity = arg
        room_id = activity.target.id
        kicked_id = activity.object.id
        ban_duration = activity.object.summary

        try:
            utils.ban_user(room_id, kicked_id, ban_duration)
        except Exception as e:
            logger.exception('could not ban user, should have been caught in validator: %s' % str(e))
            logger.error('request activity for failed ban was: %s' % str(data))


@environ.env.observer.on('on_ban')
def _on_ban_ban_user(arg: tuple) -> None:
    OnBanHooks.ban_user(arg)
