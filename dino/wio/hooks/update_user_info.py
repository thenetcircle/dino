from dino.wio import environ


class OnUpdateUserInfoHooks(object):
    @staticmethod
    def update_cache(arg: tuple) -> None:
        _, activity = arg
        environ.env.cache.reset_user_info(activity.actor.id)


@environ.env.observer.on('on_update_user_info')
def _on_update_user_info_update_cache(arg: tuple) -> None:
    OnUpdateUserInfoHooks.update_cache(arg)
