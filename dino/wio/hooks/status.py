import logging

from dino.wio import environ
from dino.wio import utils


class OnStatusHooks(object):
    logger = logging.getLogger(__name__)

    @staticmethod
    def set_status(arg: tuple) -> None:
        data, activity = arg

        user_id = activity.actor.id
        status = activity.verb

        if status == 'online':
            environ.env.db.set_user_online(user_id)

        elif status == 'invisible':
            environ.env.db.set_user_invisible(user_id)

        elif status == 'offline':
            if not utils.is_valid_id(user_id):
                OnStatusHooks.logger.warning('got invalid id on disconnect for act: {}'.format(str(activity.id)))
                return
            environ.env.db.set_user_offline(user_id)

        environ.env.publish(data, external=True)


@environ.env.observer.on('on_status')
def _on_status_set_status(arg: tuple) -> None:
    OnStatusHooks.set_status(arg)
