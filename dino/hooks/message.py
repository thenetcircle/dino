# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from typing import Union

from dino import environ
from dino import utils
from dino.config import ConfigKeys
from dino.exceptions import NoSuchUserException
from dino.utils.decorators import timeit

import logging
import traceback
import json
import sys
import emoji
import re

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


class OnMessageHooks(object):
    @staticmethod
    def do_process(arg: tuple) -> None:
        def send(_data: dict, _room: str, _json: bool=True, _broadcast: bool=True) -> None:
            environ.env.emit('message', _data, json=_json, room=_room, broadcast=_broadcast)

        def publish_activity() -> None:
            user_name = activity.actor.display_name
            if utils.is_base64(user_name):
                user_name = utils.b64d(user_name)

            activity_json = utils.activity_for_message(user_id, user_name, message_id=activity.id)
            environ.env.publish(activity_json, external=True)

        def broadcast():
            room_id = activity.target.id
            if utils.user_is_invisible(user_id):
                data['actor']['attachments'] = utils.get_user_info_attachments_for(user_id)

            if activity.target.object_type == 'private':
                owners = environ.env.db.get_owners_room(activity.target.id)
                if owners is None or len(owners) == 0:
                    send(data, _room=room_id)
                else:
                    for owner in owners:
                        send(data, _room=owner)
            else:
                parsed_message = utils.parse_message(activity.object.content)
                
                if parsed_message is not None and utils.is_whisper(parsed_message):
                    logger.info("parsed whisper message: {}".format(parsed_message))

                    whisper_users = utils.get_whisper_users_from_message(parsed_message)
                    admins = environ.env.db.get_admins_in_room(activity.target.id)

                    if len(admins):
                        whisper_users.update(admins)

                    for whisper_user_name in utils.get_whisper_users_from_message(parsed_message):
                        logger.info("sending whisper to user {}".format(whisper_user_name))

                        try:
                            whisper_user_id = environ.env.db.get_user_id(whisper_user_name)
                            send(data, _room=whisper_user_id)
                        except NoSuchUserException:
                            pass

                    # also send to the sender
                    logger.info("sending whisper back to sender {}".format(user_id))
                    send(data, _room=user_id)
                else:
                    send(data, _room=room_id)

        def store(deleted=False) -> Union[str, None]:
            try:
                message_id = environ.env.storage.store_message(activity, deleted=deleted)
            except Exception as e:
                logger.error('could not store message %s because: %s' % (activity.id, str(e)))
                logger.error(str(data))
                logger.exception(traceback.format_exc())
                environ.env.capture_exception(sys.exc_info())
                return

            if not environ.env.config.get(ConfigKeys.DELIVERY_GUARANTEE, False) or \
                    activity.target.object_type != 'private':
                return

            owners = environ.env.db.get_owners_room(activity.target.id)
            environ.env.storage.mark_as_read({activity.id}, activity.actor.id, activity.target.id)
            if owners is None or len(owners) == 0:
                return

            for receiver_id in owners:
                if activity.actor.id == receiver_id:
                    continue
                environ.env.storage.mark_as_unacked(activity.id, receiver_id, activity.target.id)

            return message_id

        def check_spam():
            def remove_emojis(text):
                return ''.join([character for character in text if character not in emoji.UNICODE_EMOJI])

            def remove_custom_emojis(text):
                return re.sub(r':[a-z0-9]*:', '', text)

            def remove_multiple_consecutive_chars(text):
                return re.sub(r'(.)\1+', r'\1', text)

            def remove_numbers(text):
                return re.sub(r'\d', r'', text)

            def remove_special_chars(text):
                text = text.strip()
                text = text.replace('*', '')
                text = text.replace('+', '')
                text = text.replace('"', '')
                text = text.replace('_', '')
                text = text.replace('\'', '')
                text = text.replace('!', '')
                text = text.replace('-', '')
                text = text.replace('/', '')
                text = text.replace(';', '')
                text = text.replace('@', '')
                text = text.replace('$', '')
                text = text.replace('%', '')
                text = text.replace('&', '')
                text = text.replace(':', '')
                text = text.replace('<', '')
                text = text.replace('>', '')
                text = text.replace('(', '')
                text = text.replace(')', '')
                return text

            def replace_umlauts(text):
                text = text.replace('å', 'a')
                text = text.replace('ä', 'a')
                text = text.replace('ö', 'o')
                text = text.replace('ß', 's')
                text = text.replace('ü', 'u')
                return text

            _is_spam = False
            _spam_id = None
            _message = None

            spam_enabled = environ.env.config.get(ConfigKeys.SPAM_CLASSIFIER, False)
            if not spam_enabled:
                return False, None

            try:
                _message = utils.b64d(activity.object.content)
                try:
                    json_body = json.loads(_message)
                    _message = json_body.get('text')
                except Exception:
                    pass  # ignore, use original
            except Exception as e:
                logger.error('could not decode message: {}'.format(str(e)))
                logger.exception(e)
                environ.env.capture_exception(sys.exc_info())
                return False, None

            if environ.env.service_config.ignore_emoji():
                try:
                    _message = remove_emojis(_message)
                    _message = remove_custom_emojis(_message)
                except Exception as e:
                    logger.error('could not check if text has emojis: {}'.format(str(e)))
                    logger.exception(e)
                    environ.env.capture_exception(sys.exc_info())

            try:
                _message = remove_multiple_consecutive_chars(_message)
                _message = remove_special_chars(_message)
                _message = remove_numbers(_message)
                _message = replace_umlauts(_message)

                _is_spam, _y_hats = environ.env.spam.is_spam(_message)
                if _is_spam and environ.env.service_config.should_save_spam():
                    _spam_id = environ.env.db.save_spam_prediction(activity, _message, _y_hats)
            except Exception as e:
                logger.error('could not predict spam: {}'.format(str(e)))
                logger.exception(e)
                environ.env.capture_exception(sys.exc_info())
                return False, None

            return _is_spam, _spam_id

        data, activity = arg
        user_id = activity.actor.id

        # for wio we don't check for spam or blacklist
        if 'wio' in environ.env.config.get(ConfigKeys.ENVIRONMENT, 'default'):
            store(deleted=False)
            broadcast()
            publish_activity()
            return

        user_used_blacklisted_word, word_used_if_any = utils.used_blacklisted_word(activity)

        if user_used_blacklisted_word:
            blacklist_activity = utils.activity_for_blacklisted_word(activity, word_used_if_any)
            environ.env.publish(blacklist_activity, external=True)
            send(data, _room=user_id, _broadcast=False)

            admins_in_room = environ.env.db.get_admins_in_room(activity.target.id)
            if len(admins_in_room) > 0:
                for admin_user_id in admins_in_room:
                    send(data, _room=admin_user_id, _broadcast=False)
        else:
            is_spam, spam_id = check_spam()

            if is_spam and environ.env.service_config.is_spam_classifier_enabled():
                spam_activity = utils.activity_for_spam_word(activity)
                environ.env.publish(spam_activity, external=True)

                if environ.env.service_config.should_delete_spam():
                    store(deleted=True)
                else:
                    store(deleted=False)
                    broadcast()
                    publish_activity()

            else:
                store(deleted=False)
                broadcast()
                publish_activity()


@environ.env.observer.on('on_message')
@timeit(logger, 'on_message_hooks')
def _on_message_broadcast(arg: tuple) -> None:
    OnMessageHooks.do_process(arg)
