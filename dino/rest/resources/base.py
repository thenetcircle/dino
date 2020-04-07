from datetime import datetime
from flask_restful import Resource

import logging
import traceback

logger = logging.getLogger(__name__)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class BaseResource(Resource):
    def __init__(self, cache_clear_interval=2):
        self.cache_clear_interval = cache_clear_interval

    def get(self):
        if (datetime.utcnow() - self._get_last_cleared()).total_seconds() > self.cache_clear_interval:
            self._get_lru_method().cache_clear()
            self._set_last_cleared(datetime.utcnow())

        try:
            return {'status_code': 200, 'data': self.do_get()}
        except Exception as e:
            logger.error('could not do get: %s' % str(e))
            logger.exception(traceback.format_exc())
            return {'status_code': 500, 'data': str(e)}

    def post(self):
        try:
            data = self.do_post()
            return_value = {'status_code': 200}
            if data is not None:
                return_value['data'] = data
            return return_value
        except Exception as e:
            logger.error('could not do get: %s' % str(e))
            logger.exception(traceback.format_exc())
            return {'status_code': 500, 'data': str(e)}

    def delete(self):
        try:
            data = self.do_delete()
            return_value = {'status_code': 200}
            if data is not None:
                return_value['data'] = data
            return return_value
        except Exception as e:
            logger.error('could not do delete: %s' % str(e))
            logger.exception(traceback.format_exc())
            return {'status_code': 500, 'data': str(e)}

    def validate_json(self, request, silent=True):
        try:
            return True, None, request.get_json(silent=silent)
        except Exception as e:
            logger.error('error: %s' % str(e))
            logger.exception(traceback.format_exc())
            return False, 'invalid json in request', None

    def do_delete(self):
        raise NotImplementedError()

    def do_post(self):
        raise NotImplementedError()

    def do_get(self):
        raise NotImplementedError()

    def _get_lru_method(self):
        raise NotImplementedError()

    def _get_last_cleared(self):
        raise NotImplementedError()

    def _set_last_cleared(self, last_cleared):
        raise NotImplementedError()
