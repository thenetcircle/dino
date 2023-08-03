import logging

from dino.endpoint.base import BasePublisher

logger = logging.getLogger(__name__)


class MockPublisher(BasePublisher):
    def __init__(self, env, is_external_queue: bool):
        super().__init__(env, is_external_queue, queue_type='mock', logger=logger)

    def try_publish(self, message, topic: str = None):
        self.logger.info('sending "{}" with "{}"'.format(self.message_type, str(self.queue_connection)))

    def publish(self, message: dict, topic: str = None) -> None:
        if self.recently_sent_has(topic, message['id']):
            self.logger.debug(
                'ignoring external event with verb {} and id {}, already sent to this topic'.format(
                    message['verb'], message['id']))
            return

        self.logger.debug('published external event with verb {} id {}'.format(message['verb'], message['id']))
