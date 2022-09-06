import logging

from dino import environ
from dino.config import ConfigKeys

logger = logging.getLogger(__name__)


class OnRemoveRoomHooks(object):
    @staticmethod
    def publish_event(arg: tuple) -> None:
        _, activity = arg

        if len(environ.env.config) == 0 or environ.env.config.get(ConfigKeys.TESTING, False):
            # assume we're testing
            return

        environ.env.publish(activity, external=True)


@environ.env.observer.on('on_remove_room')
def _on_remove_room(arg) -> None:
    OnRemoveRoomHooks.publish_event(arg)
