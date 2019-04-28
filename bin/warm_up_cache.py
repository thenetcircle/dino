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

from dino.environ import env

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger('warm_up_cache.py')

logger.info('getting all user ids...')

try:
    all_users = env.db.get_all_user_ids()
    logger.info('caching all user roles...')
    env.db.get_users_roles(all_users)
except NotImplementedError:
    pass

try:
    logger.info('caching all rooms for channels...')
    channels = env.db.get_channels()
    for channel_id in channels.keys():
        env.db.rooms_for_channel(channel_id)
except NotImplementedError:
    pass

logger.info('done! cache warmed up')
