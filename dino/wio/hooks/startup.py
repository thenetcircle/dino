import logging
from datetime import datetime
from uuid import uuid4 as uuid

from dino.config import ConfigKeys
from dino.wio import environ

logger = logging.getLogger(__name__)


class OnStartupDoneHooks(object):
    @staticmethod
    def publish_startup_done_event() -> None:
        if len(environ.env.config) == 0 or environ.env.config.get(ConfigKeys.TESTING, False):
            # assume we're testing
            return

        if environ.env.node != 'rest':
            # avoid publishing duplicate events by only letting the rest node publish external events
            return

        json_event = {
            'id': str(uuid()),
            'verb': 'restart',
            'content': environ.env.config.get(ConfigKeys.ENVIRONMENT),
            'published': datetime.utcnow().strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
        }

        logger.debug('publishing restart-done event to external queue: %s' % str(json_event))
        environ.env.publish(json_event, external=True)


@environ.env.observer.on('on_startup_done')
def _on_startup_done(arg) -> None:
    OnStartupDoneHooks.publish_startup_done_event()
