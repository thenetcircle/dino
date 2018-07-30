from dino.wio import environ


class OnBanHooks(object):
    @staticmethod
    def publish_activity(arg: tuple) -> None:
        data, activity = arg
        environ.env.publish(data)


@environ.env.observer.on('on_ban')
def _on_ban_ban_user(arg: tuple) -> None:
    OnBanHooks.publish_activity(arg)
