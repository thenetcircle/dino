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

import re

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class GenericValidator(object):
    @staticmethod
    def is_digit(val: str):
        if not GenericValidator.is_string(val) or len(val) == 0:
            return False
        if val[0] in ('-', '+'):
            return val[1:].isdigit()
        return val.isdigit()

    @staticmethod
    def is_string(val: str):
        return val is not None and isinstance(val, str)

    @staticmethod
    def chars_in_list(val: str, char_list: list):
        if not GenericValidator.is_string(val):
            return False

        if len(val.strip()) == 0:
            return False

        return len([x for x in val.split(',') if x in char_list]) == len(val.split(','))

    @staticmethod
    def match(val: str, regex: str):
        return GenericValidator.is_string(val) and re.match(regex, val) is not None
