#!/usr/bin/env python

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

import logging
import traceback

from dino import environ
from dino import utils
from dino.rest.resources.base import BaseResource

from flask import request

logger = logging.getLogger(__name__)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class BlacklistResource(BaseResource):
    def __init__(self):
        super(BlacklistResource, self).__init__()
        self.request = request

    def do_post(self):
        is_valid, msg, json = self.validate_json()
        if not is_valid:
            logger.error('invalid json: %s' % msg)
            raise RuntimeError('invalid json')

        if json is None:
            raise RuntimeError('no json in request')
        if not isinstance(json, dict):
            raise RuntimeError('need a dict')
        logger.debug('POST request: %s' % str(json))

        if 'word' not in json:
            raise RuntimeError('no id parameter in request')

        word = json.get('word')
        if not utils.is_base64(word):
            logger.error('word is not base64 encoded: "%s"' % word)
            raise RuntimeError('word is not base64 encoded: "%s"' % word)

        try:
            word = utils.b64d(word)
        except Exception as e:
            logger.error('could not decode base64 word "%s": %s' % (str(word), str(e)))
            raise RuntimeError('could not decode base64 word "%s": %s' % (str(word), str(e)))

        try:
            environ.env.db.add_words_to_blacklist([word])
        except Exception as e:
            logger.error('could not add word "%s" to blacklist: %s' % (str(word), str(e)))
            logger.exception(traceback.format_exc())
            raise RuntimeError('could not add word "%s" to blacklist: %s' % (str(word), str(e)))

    def do_delete(self):
        is_valid, msg, json = self.validate_json()
        if not is_valid:
            logger.error('invalid json: %s' % msg)
            raise RuntimeError('invalid json')

        if json is None:
            raise RuntimeError('no json in request')
        if not isinstance(json, dict):
            raise RuntimeError('need a dict')
        logger.debug('DELETE request: %s' % str(json))

        if 'word' not in json:
            raise RuntimeError('no id parameter in request')

        word = json.get('word')
        if not utils.is_base64(word):
            logger.error('word is not base64 encoded: "%s"' % word)
            raise RuntimeError('word is not base64 encoded: "%s"' % word)

        try:
            word = utils.b64d(word)
        except Exception as e:
            logger.error('could not decode base64 word "%s": %s' % (str(word), str(e)))
            raise RuntimeError('could not decode base64 word "%s": %s' % (str(word), str(e)))

        try:
            environ.env.db.remove_matching_word_from_blacklist(word)
        except Exception as e:
            logger.error('could not remove word "%s" from blacklist: %s' % (str(word), str(e)))
            logger.exception(traceback.format_exc())
            raise RuntimeError('could not remove word "%s" from blacklist: %s' % (str(word), str(e)))

    def validate_json(self):
        try:
            return True, None, self.request.get_json(silent=False)
        except Exception as e:
            logger.error('error: %s' % str(e))
            logger.exception(traceback.format_exc())
            return False, 'invalid json in request', None
