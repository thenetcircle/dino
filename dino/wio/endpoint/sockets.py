import logging
import sys
import threading
import time
import traceback
from typing import Union

import activitystreams as as_parser
from activitystreams.models.activity import Activity
from flask_socketio import disconnect
from kombu.mixins import ConsumerMixin

from dino.config import ConfigKeys
from dino.utils.decorators import count_connections
from dino.utils.decorators import pre_process
from dino.utils.decorators import respond_with
from dino.utils.handlers import GracefulInterruptHandler
from dino.wio import api
from dino.wio import environ
from dino.wio.endpoint.queue import WioQueueHandler
from dino.wio.server import socketio

logger = logging.getLogger(__name__)
queue_handler = WioQueueHandler(socketio, environ.env)


class Worker(ConsumerMixin):
    def __init__(self, connection, signal_handler: GracefulInterruptHandler):
        self.connection = connection
        self.signal_handler = signal_handler

    def get_consumers(self, consumer, channel):
        return [consumer(queues=[environ.env.queue], callbacks=[self.process_task])]

    def on_iteration(self):
        if self.signal_handler.interrupted:
            self.should_stop = True

    def process_task(self, body, message):
        try:
            queue_handler.handle_server_activity(body, as_parser.parse(body))
        except Exception as e:
            logger.error('could not parse server message: "%s", message was: %s' % (str(e), body))
            environ.env.capture_exception(sys.exc_info())
        message.ack()


def consume():
    if len(environ.env.config) == 0 or environ.env.config.get(ConfigKeys.TESTING, False):
        return

    with GracefulInterruptHandler() as interrupt_handler:
        while True:
            with environ.env.queue_connection as conn:
                try:
                    logger.info('setting up consumer "{}"'.format(str(environ.env.queue_connection)))
                    environ.env.consume_worker = Worker(conn, interrupt_handler)
                    environ.env.consume_worker.run()
                except KeyboardInterrupt:
                    return

            if interrupt_handler.interrupted or environ.env.consume_worker.should_stop:
                return

            time.sleep(0.1)


if not environ.env.config.get(ConfigKeys.TESTING, False):
    def disconnect_by_sid(sid: str) -> None:
        if sid is None:
            raise ValueError('need sid to disconnect client')
        environ.env._force_disconnect_by_sid(sid, '/ws')

    environ.env._force_disconnect_by_sid = socketio.server.disconnect
    environ.env.disconnect_by_sid = disconnect_by_sid
    environ.env.consume_thread = threading.Thread(target=consume)
    environ.env.consume_thread.start()


@socketio.on_error('/ws')
def error_handler_chat(e):
    try:
        environ.env.capture_exception(e)
    except Exception as capture_e:
        logger.error('could not capture exception: %s' % str(capture_e))
        logger.exception(traceback.format_exc(capture_e))
        logger.error('exception to capture was: %s' % str(e))
        logger.exception(traceback.format_exc(e))


# no pre-processing for connect event
@socketio.on('connect', namespace='/ws')
@respond_with('gn_connect')
@count_connections('connect')
def connect() -> (int, None):
    return api.connect()


@socketio.on('login', namespace='/ws')
@respond_with('gn_login', should_disconnect=True)
@pre_process('on_login', should_validate_request=False)
def on_login(data: dict, activity: Activity) -> (int, str):
    try:
        status_code, msg = api.on_login(data, activity)
        if status_code != 200:
            disconnect()
        return status_code, msg
    except Exception as e:
        logger.error('could not login, will disconnect client: %s' % str(e))
        logger.exception(traceback.format_exc())
        environ.env.capture_exception(sys.exc_info())
        return 500, str(e)


@socketio.on('update_user_info', namespace='/ws')
@respond_with('gn_update_user_info')
@pre_process('on_update_user_info')
def on_update_user_info(data: dict, activity: Activity) -> (int, Union[str, dict, None]):
    return api.on_update_user_info(data, activity)


@socketio.on('status', namespace='/ws')
@respond_with('gn_status')
@pre_process('on_status')
def on_status(data: dict, activity: Activity) -> (int, Union[str, dict, None]):
    return api.on_status(data, activity)


# no pre-processing for disconnect event
@socketio.on('disconnect', namespace='/ws')
@count_connections('disconnect')
def on_disconnect() -> (int, None):
    return api.on_disconnect()
