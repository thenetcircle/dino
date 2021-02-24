import logging
import traceback
from datetime import datetime

from activitystreams import parse as parse_to_as
from flask_restful import Resource

from dino.utils import ActivityBuilder

logger = logging.getLogger(__name__)



def join_activity(actor_id: str, target_id: str, session_ids: list, namespace: str) -> dict:
    return ActivityBuilder.enrich({
        "actor": {
            "id": actor_id,
            "content": ",".join(session_ids),
            "url": namespace
        },
        "verb": "join",
        "target": {
            "id": target_id
        }
    })


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


class RoomNameBaseResource(BaseResource):
    def __init__(self, env):
        super(RoomNameBaseResource, self).__init__()
        self.env = env

    def join(self, user_id, room_id):
        session_ids = self.env.db.get_sids_for_user(user_id)

        if len(session_ids) == 0:
            logger.warning("no sessions found for user {}, can not join room {}".format(user_id, room_id))
            return

        if len(session_ids) > 1:
            logger.warning("multiple session ids found for user {}, will make all join".format(user_id))

        data = join_activity(user_id, room_id, session_ids, self.namespace)
        activity = parse_to_as(data)

        # reuse existing logic for joining the room
        self.env.observer.emit("on_join", (data, activity))
