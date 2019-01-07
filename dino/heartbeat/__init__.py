from abc import ABC


class IHeartbeatManager(ABC):
    def add_heartbeat(self, user_id: str, sid: str) -> None:
        raise NotImplementedError()
