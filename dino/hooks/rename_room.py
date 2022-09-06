import logging

from dino import environ
from dino.config import ConfigKeys

logger = logging.getLogger(__name__)


class OnRenameRoomHooks(object):
    @staticmethod
    def publish_event(arg: tuple) -> None:
        _, activity = arg

        json_act = {
            'id': activity.id,
            'published': activity.published,
            'actor': {
                'id': activity.actor.id,
                'displayName': activity.actor.display_name
            },
            'target': {
                'id': activity.target.id,
                'displayName': activity.target.display_name,
                'objectType': activity.target.object_type
            },
            'object': {
                'content': activity.object.content,
                'objectType': activity.object.object_type
            },
            'verb': activity.verb,
            'provider': {
                'id': activity.provider.id
            }
        }

        if len(environ.env.config) == 0 or environ.env.config.get(ConfigKeys.TESTING, False):
            # assume we're testing
            return

        environ.env.publish(json_act, external=True)


@environ.env.observer.on('on_rename_room')
def _on_rename_room(arg) -> None:
    OnRenameRoomHooks.publish_event(arg)
