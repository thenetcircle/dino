import hashlib
import logging
import sys
import traceback

from jsonrpcclient.clients.http_client import HTTPClient
from jsonrpcclient.requests import Request

from dino.config import ConfigKeys
from dino.environ import GNEnvironment
from dino.remote import IRemoteHandler


class RemoteHandler(IRemoteHandler):
    def __init__(self, env: GNEnvironment):
        self.env = env
        self.logger = logging.getLogger(__name__)
        self.host = env.config.get(ConfigKeys.HOST, domain=ConfigKeys.REMOTE)
        self.path_whisper = env.config.get(ConfigKeys.PATH_CAN_WHISPER, domain=ConfigKeys.REMOTE)
        self.private_key = env.config.get(ConfigKeys.PRIVATE_KEY, domain=ConfigKeys.REMOTE)

    def can_send_whisper_to(self, sender_id: str, target_user_name: str) -> bool:
        url = "{}/{}".format(self.host, self.path_whisper)

        # might not be an int in some applications
        try:
            sender_id = int(sender_id)
        except ValueError:
            pass

        try:
            self.logger.debug("calling url: {}".format(url))

            request = Request(
                method="whisper.validate",
                senderId=sender_id,
                receiverName=target_user_name,
            )

            request_and_hash = self.private_key + str(request)
            sign_hash = hashlib.md5(request_and_hash.encode('utf-8')).hexdigest()

            client = HTTPClient(url)
            client.session.headers.update({
                "Content-Type": "application/json-rpc",
                "X-RPC-SIGN": sign_hash
            })

            response = client.send(request).data
        except Exception as e:
            self.logger.error("could not call remote endpoint {}: {}".format(url, str(e)))
            self.env.capture_exception(sys.exc_info())
            self.logger.exception(e)
            return True

        if response is None:
            self.logger.error("received None response for jsonrpc call")
            return True

        if not response.ok:
            self.logger.error("remote jsonrpc call failed, error_msg: {}".format(str(response)))
            return True

        self.logger.debug("response for sender_id {} and target_user_name {}: {}".format(
            sender_id, target_user_name, str(response)
        ))

        # '.data' is hinted JSONRPCResponse in lib, but if successful, it's a SuccessResponse, which
        # has the 'result' variable that JSONRPCResponse doesn't, so add the 'noqa' to skip warnings
        success = response.result.get('success', 1)  # noqa
        error_msg = response.result.get('error_msg', '[empty error in response]')  # noqa
        error_code = response.result.get('error_msg', '-1')  # noqa

        try:
            error_code = int(float(error_code))
        except Exception as e:
            self.logger.error("could not convert error code '{}' to int: {}".format(error_code, str(e)))
            self.logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())

        errors = {
            50000: "generic error",
            50001: "only contacts can whisper",
            50002: "whisper is turned off",
        }

        if error_code in errors.keys():
            self.logger.info("got error code {} '{}' when checking whisper from {} to {}".format(
                error_code, errors.get(error_code), sender_id, target_user_name
            ))

            if error_code in {50001, 50002}:
                return False

        return success == 1
