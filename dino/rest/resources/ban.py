import logging
import sys
import traceback

from eventlet.greenpool import GreenPool
from flask import request

from dino import environ
from dino import utils
from dino.db.manager import UserManager
from dino.exceptions import NoSuchUserException
from dino.exceptions import UnknownBanTypeException
from dino.rest.resources.base import BaseResource
from dino.utils.decorators import timeit

logger = logging.getLogger(__name__)


def fail(error_message):
    return {
        'status': 'FAIL',
        'message': error_message
    }


def ok():
    return {
        'status': 'OK'
    }


class BanResource(BaseResource):
    def __init__(self):
        super(BanResource, self).__init__()
        self.user_manager = UserManager(environ.env)
        self.executor = GreenPool()
        self.request = request
        self.env = environ.env

    def do_post(self):
        try:
            json = self._validate_params()
            self.schedule_execution(json)
            return ok()
        except Exception as e:
            logger.error('could not ban user: %s' % str(e))
            logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            return fail(str(e))

    def schedule_execution(self, json: dict):
        try:
            # avoid hanging clients
            self.executor.spawn_n(self._do_post, json)
        except Exception as e:
            logger.error('could not schedule ban request: %s' % str(e))
            logger.exception(e)
            self.env.capture_exception(sys.exc_info())

    def _validate_params(self):
        is_valid, msg, json = self.validate_json(self.request, silent=False)
        if not is_valid:
            raise RuntimeError('invalid json: %s' % msg)

        if json is None:
            raise RuntimeError('no json in request')
        if not isinstance(json, dict):
            raise RuntimeError('need a dict of user-room keys')

        for user_id, ban_info in json.items():
            try:
                target_type = ban_info['type']
            except KeyError:
                raise KeyError('missing target type for user id %s and request %s' % (user_id, ban_info))

            # 'target' is for backwards compatibility; new versions user either room_id or room_name
            if 'target' not in ban_info and 'room_id' not in ban_info and 'room_name' not in ban_info:
                if target_type != 'global':
                    raise KeyError('missing target id for user id %s and request %s' % (user_id, ban_info))

            try:
                ban_info['duration']
            except KeyError:
                raise KeyError('missing ban duration for user id %s and request %s' % (user_id, ban_info))

            ban_info.get('reason')
            ban_info.get('admin_id')

        return json

    @timeit(logger, 'on_rest_ban')
    def _do_post(self, json: dict):
        logger.debug('POST request: %s' % str(json))
        for user_id, ban_info in json.items():
            try:
                self.ban_user(user_id, ban_info)
            except Exception as e:
                self.env.capture_exception(sys.exc_info())
                logger.error('could not ban user %s: %s' % (user_id, str(e)))

    def ban_user(self, user_id: str, ban_info: dict):
        target_type = ban_info.get('type', '')
        duration = ban_info.get('duration', '')
        reason = ban_info.get('reason', '')
        banner_id = ban_info.get('admin_id', '')
        room_name = None

        if 'target' in ban_info:
            target_id = ban_info.get('target')

        elif 'room_id' in ban_info:
            target_id = ban_info.get('room_id')

        # already validated that one of the three is in the request
        else:
            room_name = ban_info.get('room_name')
            room_name = utils.b64d(room_name)
            target_id = utils.get_room_id(room_name, use_default_channel=True)

        try:
            user_name = ban_info['name']
            user_name = utils.b64d(user_name)
        except KeyError:
            logger.warning('no name specified in ban info, if we have to create the user it will get the ID as name')
            user_name = user_id

        try:
            self.user_manager.ban_user(
                user_id, target_id, duration, target_type,
                reason=reason, banner_id=banner_id,
                user_name=user_name, target_name=room_name
            )

        except ValueError as e:
            logger.error('invalid ban duration "%s" for user %s: %s' % (duration, user_id, str(e)))
            self.env.capture_exception(sys.exc_info())

        except NoSuchUserException as e:
            logger.error('no such user %s: %s' % (user_id, str(e)))
            self.env.capture_exception(sys.exc_info())

        except UnknownBanTypeException as e:
            logger.error('unknown ban type "%s" for user %s: %s' % (target_type, user_id, str(e)))
            self.env.capture_exception(sys.exc_info())

        except Exception as e:
            logger.error('could not ban user %s: %s' % (user_id, str(e)))
            logger.error(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
