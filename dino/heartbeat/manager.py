import time
import traceback

import eventlet
import logging

import sys
from activitystreams import parse as parse_to_as

from eventlet.semaphore import Semaphore
from datetime import datetime as dt
from datetime import timedelta

from dino.config import ConfigKeys
from dino.endpoint.base import locked_method
from dino.environ import GNEnvironment
from dino.heartbeat import IHeartbeatManager

logger = logging.getLogger(__name__)


class HeartbeatManager(IHeartbeatManager):
    def __init__(self, env: GNEnvironment):
        self._lock = Semaphore(value=1)
        self.env = env
        self.to_check = dict()
        self.heartbeat_sids = set()

        self.expire_second = env.config.get(ConfigKeys.TIMEOUT, domain=ConfigKeys.HEARTBEAT, default=300)
        self.sleep_time = env.config.get(ConfigKeys.INTERVAL, domain=ConfigKeys.HEARTBEAT, default=20)

        eventlet.spawn_after(func=self.loop, seconds=10)

    def loop(self):
        while True:
            try:
                expired = self.get_all_expired_user_ids()
                self.check_heartbeats(expired)
                time.sleep(self.sleep_time)
            except InterruptedError:
                logger.info('interrupted, exiting loop')
                break
            except Exception as e:
                logger.error('could not check heartbeat: {}'.format(str(e)))
                logger.exception(traceback.format_exc())
                self.env.capture_exception(sys.exc_info())
                time.sleep(1)

    def check_heartbeats(self, user_ids: list) -> None:
        for user_id in user_ids:
            still_online = self.env.cache.check_heartbeat(user_id)

            if still_online:
                self.add_heartbeat(user_id)
                continue

            hb_sid = 'hb-{}'.format(user_id)
            data = {
                'verb': 'disconnect',
                'actor': {
                    'id': user_id,
                    'content': hb_sid
                }
            }

            if not self.env.config.get(ConfigKeys.TESTING):
                # only used for single-session restrictions
                if self.env.connected_user_ids.get(user_id) == hb_sid:
                    del self.env.connected_user_ids[user_id]

            activity = parse_to_as(data)
            self.env.observer.emit('on_heartbeat_disconnect', (data, activity))

    @locked_method
    def has_heartbeat(self, user_id: str) -> bool:
        return user_id in self.to_check.keys()

    @locked_method
    def add_heartbeat(self, user_id: str) -> None:
        self.to_check[user_id] = dt.utcnow()

    @locked_method
    def get_all_expired_user_ids(self):
        expired = list()
        not_yet_expired = dict()
        now_time = dt.utcnow() - timedelta(seconds=self.expire_second)

        for user_id, add_time in self.to_check.items():
            if add_time < now_time:
                expired.append(user_id)
            else:
                not_yet_expired[user_id] = add_time

        self.to_check = not_yet_expired.copy()
        return expired.copy()
