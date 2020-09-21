from dino.remote import IRemoteHandler


class MockHandler(IRemoteHandler):
    def can_send_whisper_to(self, sender_id: str, target_user_name: str) -> (bool, int):
        return True
