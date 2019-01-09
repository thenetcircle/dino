from abc import ABC


class IHeartbeatManager(ABC):
    def loop(self):
        raise NotImplementedError()

    def check_heartbeats(self, user_ids: list) -> None:
        raise NotImplementedError()

    def has_heartbeat(self, user_id: str) -> bool:
        raise NotImplementedError()

    def add_heartbeat(self, user_id: str) -> None:
        raise NotImplementedError()

    def get_all_expired_user_ids(self):
        raise NotImplementedError()
