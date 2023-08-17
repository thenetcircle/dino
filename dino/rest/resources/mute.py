import logging
import sys
import traceback

from eventlet.greenpool import GreenPool
from flask import request

from dino import environ
from dino import utils
from dino.db.manager import UserManager
from dino.exceptions import NoSuchUserException, NoSuchRoomException
from dino.rest.resources.base import BaseResource

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


class MuteResource(BaseResource):
    def __init__(self):
        super(MuteResource, self).__init__()
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
            logger.error('could not mute user: %s' % str(e))
            logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            return fail(str(e))

    def do_delete(self):
        try:
            is_valid, msg, json = self.validate_json(self.request, silent=False)
            if not is_valid or 'user_id' not in json:
                raise RuntimeError('invalid json: %s' % msg)

            user_id = str(int(float(json.get('user_id'))))
            room_id = None
            room_name = None

            if 'room_id' in json:
                room_id = json.get('room_id')
            if 'room_name' in json:
                room_name = utils.b64d(json.get('room_name'))

            if room_id is None and room_name is None:
                raise RuntimeError('invalid json: no room name or room id in unmute request')

            self.user_manager.remove_mute(user_id, room_id, room_name)
            return ok()

        except NoSuchRoomException as e:
            logger.error('could not mute user: %s' % str(e))
            logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            return fail(f"no room exists with name: {str(e.uuid)}")

        except Exception as e:
            logger.error('could not mute user: %s' % str(e))
            logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            return fail(str(e))

    def schedule_execution(self, json: dict):
        try:
            # avoid hanging clients
            self.executor.spawn_n(self._do_post, json)
        except Exception as e:
            logger.error('could not schedule mute request: %s' % str(e))
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

        for user_id, mute_info in json.items():
            if 'room_id' not in mute_info and 'room_name' not in mute_info:
                raise KeyError(f'missing both room id and name in request: {mute_info}')

            try:
                mute_info['duration']
            except KeyError:
                raise KeyError('missing mute duration for user id %s and request %s' % (user_id, mute_info))

        return json

    def _do_post(self, json: dict):
        logger.debug('POST request: %s' % str(json))
        for user_id, mute_info in json.items():
            try:
                self.mute_user(user_id, mute_info)
            except Exception as e:
                logger.error('could not mute user %s: %s' % (user_id, str(e)))
                logger.exception(e)
                self.env.capture_exception(sys.exc_info())

    def mute_user(self, user_id: str, mute_info: dict):
        duration = mute_info.get('duration', '')
        reason = mute_info.get('reason', '')
        muter_id = mute_info.get('muter_user_id', '')
        room_name = mute_info.get('room_name', '')

        if 'room_id' in mute_info:
            room_id = mute_info.get('room_id')

        elif 'room_name' in mute_info:
            room_name = mute_info.get('room_name')
            room_name = utils.b64d(room_name)
            room_id = utils.get_room_id(room_name, use_default_channel=True)

        else:
            logger.error(f"no room_id or room_name in request, can't mute user: {mute_info}")
            return

        try:
            self.user_manager.mute_user(
                user_id=user_id, room_id=room_id, duration=duration,
                reason=reason, muter_id=muter_id, room_name=room_name
            )

        except ValueError as e:
            logger.error('invalid mute duration "%s" for user %s: %s' % (duration, user_id, str(e)))
            self.env.capture_exception(sys.exc_info())

        except NoSuchUserException as e:
            logger.error('no such user %s: %s' % (user_id, str(e)))
            self.env.capture_exception(sys.exc_info())

        except Exception as e:
            logger.error('could not mute user %s: %s' % (user_id, str(e)))
            logger.error(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
