import logging

from dino.db.manager.base import BaseManager
from dino.environ import GNEnvironment

logger = logging.getLogger(__name__)


class UserManager(BaseManager):
    def __init__(self, env: GNEnvironment):
        self.env = env

    def auth_user(self, user_id, _):
        self.env.cache.add_heartbeat(user_id)
        self.env.heartbeat.add_heartbeat(user_id)
