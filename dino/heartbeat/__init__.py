from abc import ABC


class IHeartbeatManager(ABC):
    def add_heartbeat(self, user_id: str) -> None:
        raise NotImplementedError()
