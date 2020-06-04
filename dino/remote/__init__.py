from abc import ABC


class IRemoteHandler(ABC):
    def can_send_whisper_to(self, sender_id: str, target_user_name: str) -> (bool, int):
        raise NotImplementedError()
