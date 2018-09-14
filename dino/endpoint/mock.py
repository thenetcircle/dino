from dino.endpoint.base import BasePublisher


class MockPublisher(BasePublisher):
    def __init__(self, env, is_external_queue: bool):
        super().__init__(env, is_external_queue, queue_type='mock', logger=None)
