from loguru import logger

from dino.environ import env

days = 0
logger.info('caching last {} days of online time...'.format(days))

try:
    last_online_times = env.db.get_last_online_since(days=days)
    logger.info('caching all last online time for {} users...'.format(len(last_online_times)))
    env.cache.set_last_online(last_online_times)
except NotImplementedError:
    pass

logger.info('done! cache warmed up')
