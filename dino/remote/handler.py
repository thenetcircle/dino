from dino.config import ConfigKeys

from dino.remote import IRemoteHandler
import requests
import logging

import sys
from dino.environ import GNEnvironment


class RemoteHandler(IRemoteHandler):
    def __init__(self, env: GNEnvironment):
        self.env = env
        self.logger = logging.getLogger(__name__)
        self.host = env.config.get(ConfigKeys.HOST, domain=ConfigKeys.REMOTE)
        self.path_can_whisper = env.config.get(ConfigKeys.PATH_CAN_WHISPER, domain=ConfigKeys.REMOTE)

    def can_send_whisper_to(self, sender_id: str, target_user_name: str) -> bool:
        url = "{}/{}/sender/{}/receiver/{}".format(
            self.host, self.path_can_whisper, sender_id, target_user_name
        )

        try:
            self.logger.debug("calling url: {}".format(url))
            response = requests.get(url)
        except Exception as e:
            self.logger.error("could not call remote endpoint {}: {}".format(url, str(e)))
            self.env.capture_exception(sys.exc_info())
            self.logger.exception(e)
            return True

        self.logger.debug("response for sender_id {} and target_user_name {}: {}".format(
            sender_id, target_user_name, str(response.content)
        ))

        # TODO: check response schema
        return response.content == "yes"
