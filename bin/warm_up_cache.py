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
    logger.info('caching all user roles ({})...'.format(len(all_users)))
    env.db.get_users_roles(all_users)
except NotImplementedError:
    pass

try:
    channels = env.db.get_channels()
    logger.info('caching all rooms for channels ({})...'.format(len(channels)))
    for channel_id in channels.keys():
        env.db.rooms_for_channel(channel_id)
        env.db.get_acls_in_channel_for_action(channel_id, 'list')
except NotImplementedError:
    pass

try:
    last_online_times = env.db.get_last_online_since(days=7)
    logger.info('caching all last online time for {} users...'.format(len(last_online_times)))
    env.cache.set_last_online(last_online_times)
except NotImplementedError:
    pass

logger.info('done! cache warmed up')
