import logging

from dino import environ
from dino.config import ConfigKeys

logger = logging.getLogger(__name__)


class OnRenameRoomHooks(object):
    @staticmethod
    def publish_event(arg: tuple) -> None:
        _, activity = arg

        if len(environ.env.config) == 0 or environ.env.config.get(ConfigKeys.TESTING, False):
            # assume we're testing
            return

        logger.debug('publishing rename room event to external queue: %s' % str(activity))
        environ.env.publish(activity, external=True)


@environ.env.observer.on('on_rename_room')
def _on_rename_room(arg) -> None:
    OnRenameRoomHooks.publish_event(arg)
