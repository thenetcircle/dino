import logging
import traceback
from yapsy.IPlugin import IPlugin
from activitystreams.models.activity import Activity

from dino import utils
from dino.config import ErrorCodes
from dino.config import ConfigKeys
from dino.environ import GNEnvironment

logger = logging.getLogger(__name__)


class OnCreateCheckAmountOfPrivateRooms(IPlugin):
    def __init__(self):
        super(OnCreateCheckAmountOfPrivateRooms, self).__init__()
        self.env = None
        self.enabled = False
        self.min_length = 3
        self.max_length = 120

    def setup(self, env: GNEnvironment):
        self.env = env
        try:
            on_create_config = self.env.config.get(ConfigKeys.VALIDATION).get('on_create').get('limit_amount')
        except Exception:
            logger.info('no config enabled for plugin limit_amount, ignoring plugin')
            return

        self.enabled = True
        self.max_rooms = on_create_config.get(ConfigKeys.MAX_ROOMS, 3)

    def _process(self, data: dict, activity: Activity):
        rooms = self.env.db.get_temp_rooms_user_is_owner_for(activity.actor.id)
        if len(rooms) >= self.max_rooms:
            return False, ErrorCodes.TOO_MANY_PRIVATE_ROOMS, 'too many private rooms for user'
        return True, None, None

    def __call__(self, *args, **kwargs) -> (bool, str):
        if not self.enabled:
            return

        data, activity = args[0], args[1]
        try:
            return self._process(data, activity)
        except Exception as e:
            logger.error('could not execute plugin not_full: %s' % str(e))
            logger.exception(traceback.format_exc())
            return False, ErrorCodes.VALIDATION_ERROR, 'could not execute validation plugin not_full'
