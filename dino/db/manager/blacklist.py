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

from dino.db.manager.base import BaseManager
from dino.environ import GNEnvironment

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


class BlackListManager(BaseManager):
    def __init__(self, env: GNEnvironment):
        self.env = env

    def get_black_list(self) -> list:
        return self.env.db.get_black_list_with_ids()

    def add_words(self, words):
        if words is None or len(words.split()) == 0:
            return
        words = set(words.split('\n'))
        self.env.db.add_words_to_blacklist(words)

    def remove_word(self, word_id):
        self.env.db.remove_word_from_blacklist(word_id)