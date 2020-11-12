import logging
import os
import sys

from dino.config import ConfigKeys

from dino.environ import env

DEFAULT_DAYS = 31

logger = logging.getLogger('warm_up_cache.py')

try:
    days = env.config.get(ConfigKeys.WARMUP_DAYS, domain=ConfigKeys.CACHE_SERVICE, default=-1)
    if days != -1:
        try:
            days = int(float(days))
        except Exception as e1:
            logger.error("could not parse configured days {}: {}".format(days, str(e)))
            days = -1

    if days < 0:
        days = os.getenv('DINO_DAYS')
        if days is None:
            if len(sys.argv) > 1:
                days = sys.argv[1]
            else:
                days = DEFAULT_DAYS

        try:
            days = int(float(days))
        except ValueError as e:
            logger.error("invalid days: {}: {}, using default value of {}".format(days, str(e), DEFAULT_DAYS))
            days = DEFAULT_DAYS
except Exception as e:
    logger.error("could not get days: {}".format(str(e)))
    days = DEFAULT_DAYS

logger.info('caching all user ids...')

try:
    all_users = env.db.get_all_user_ids()
    logger.info('caching all user roles ({})...'.format(len(all_users)))
    env.db.get_users_roles(all_users)
except NotImplementedError:
    pass

logger.info('caching all rooms...')

try:
    channels = env.db.get_channels()
    logger.info('caching all rooms for channels ({})...'.format(len(channels)))
    for channel_id in channels.keys():
        env.db.rooms_for_channel(channel_id)
        env.db.get_acls_in_channel_for_action(channel_id, 'list')
except NotImplementedError:
    pass

logger.info('caching last {} days of online time...'.format(days))

try:
    last_online_times = env.db.get_last_online_since(days=days)
    logger.info('caching all last online time for {} users...'.format(len(last_online_times)))
    env.cache.set_last_online(last_online_times)
except NotImplementedError:
    pass

logger.info('done! cache warmed up')
