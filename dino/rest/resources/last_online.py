from datetime import datetime
from flask import request

import logging
import traceback

from dino.rest.resources.base import BaseResource
from dino.utils.decorators import timeit
from dino import environ

logger = logging.getLogger(__name__)


class LastOnlineResource(BaseResource):
    def __init__(self):
        super(LastOnlineResource, self).__init__(cache_clear_interval=30)
        self.last_cleared = datetime.utcnow()
        self.request = request

    def _get_lru_method(self):
        return self.do_get_with_params

    def _get_last_cleared(self):
        return self.last_cleared

    def _set_last_cleared(self, last_cleared):
        self.last_cleared = last_cleared

    def do_get_with_params(self, user_id):
        return environ.env.db.get_last_online(user_id)

    @timeit(logger, 'on_rest_roles')
    def do_get(self):
        is_valid, msg, json = self.validate_json()
        if not is_valid:
            logger.error('invalid json: %s' % msg)
            return dict()

        if json is None:
            logger.error('no json in request')
            return dict()

        if 'user_id' not in json:
            logger.error('no "user_id" in json')
            return dict()

        logger.debug('GET request: %s' % str(json))
        user_id = json.get("user_id")

        return {
            "user_id": user_id,
            "online_at": self.do_get_with_params(user_id)
        }

    def validate_json(self):
        try:
            return True, None, self.request.get_json(silent=True)
        except Exception as e:
            logger.error('error: %s' % str(e))
            logger.exception(traceback.format_exc())
            return False, 'invalid json in request', None
