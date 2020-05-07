from dino.remote import IRemoteHandler


class RemoteHandler(IRemoteHandler):
    def __init__(self, env):
        self.env = env

    def can_send_whisper_to(self, sender_id: str, target_user_name: str) -> bool:
        return True
