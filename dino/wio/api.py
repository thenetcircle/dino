#!/usr/bin/env python

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from activitystreams import Activity
from activitystreams import parse as as_parser
import logging
from typing import Union

from dino.config import SessionKeys, ConfigKeys
from dino.wio import environ
from dino.wio import utils
from dino.wio.hooks import *
from flask import request

from dino.config import ErrorCodes as ECodes
from dino.wio.utils.decorators import timeit

__author__ = 'Oscar Eriksson <oscar@gmail.com>'

logger = logging.getLogger(__name__)


def connect() -> (int, None):
    """
    connect to the server

    :return: {'status_code': 200}
    """
    return ECodes.OK, None


@timeit(logger, 'on_login')
def on_login(data: dict, activity: Activity) -> (int, Union[str, None]):
    """
    event sent directly after a connection has successfully been made, to get the user_id for this connection

    :param data: activity streams format, needs actor.id (user id) and actor.summary (user name)
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<some error message>'}
    """
    user_id = environ.env.session.get(SessionKeys.user_id.value)
    user_name = environ.env.session.get(SessionKeys.user_name.value)

    response = utils.activity_for_login(user_id, user_name)
    environ.env.observer.emit('on_login', (data, activity))
    return ECodes.OK, response


@timeit(logger, 'on_update_user_info')
def on_update_user_info(data: dict, activity: Activity) -> (int, Union[str, None]):
    """
    broadcast a user info update to a room, or all rooms the user is in if no target.id specified

    :param data: activity streams format, must include object.attachments (user info)
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: {'status_code': ECodes.OK, 'data': '<same AS as client sent, plus timestamp>'}
    """
    activity.actor.display_name = utils.b64e(environ.env.session.get(SessionKeys.user_name.value))
    data['actor']['displayName'] = activity.actor.display_name
    environ.env.observer.emit('on_update_user_info', (data, activity))
    return ECodes.OK, data


@timeit(logger, 'on_status')
def on_status(data: dict, activity: Activity) -> (int, Union[str, None]):
    """
    change online status

    :param data: activity streams format, needs actor.id (user id), actor.summary (user name) and verb
    (online/invisible/offline)
    :param activity: the parsed activity, supplied by @pre_process decorator, NOT by calling endpoint
    :return: if ok: {'status_code': 200}, else: {'status_code': 400, 'data': '<some error message>'}
    """
    environ.env.observer.emit('on_status', (data, activity))
    return ECodes.OK, None


@timeit(logger, 'on_disconnect')
def on_disconnect() -> (int, None):
    """
    when a client disconnects or the server no longer gets a ping response from the client

    :return json if ok, {'status_code': 200}
    """
    user_id = str(environ.env.session.get(SessionKeys.user_id.value))
    data = {
        'verb': 'disconnect',
        'actor': {
            'id': user_id
        }
    }
    if not environ.env.config.get(ConfigKeys.TESTING):
        if environ.env.connected_user_ids.get(user_id) == request.sid:
            del environ.env.connected_user_ids[user_id]

    activity = as_parser(data)
    environ.env.observer.emit('on_disconnect', (data, activity))
    return ECodes.OK, None
