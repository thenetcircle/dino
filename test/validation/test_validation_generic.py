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

from unittest import TestCase

from dino.validation.generic import GenericValidator

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


def s(values: str):
    return [x for x in values]

v = GenericValidator


class GenericValidatorTest(TestCase):
    def test_chars_in_list(self):
        self.assertTrue(v.chars_in_list('a', s('abc')))

    def test_not_in_list(self):
        self.assertFalse(v.chars_in_list('a', s('bcd')))

    def test_empty_val(self):
        self.assertFalse(v.chars_in_list('', s('abc')))

    def test_none_val(self):
        self.assertFalse(v.chars_in_list(None, s('abc')))

    def test_not_string_val(self):
        self.assertFalse(v.chars_in_list(1234, s('abc')))

    def test_available_list_is_empty(self):
        self.assertFalse(v.chars_in_list('a', []))

    def test_blank_empty_list_is_still_false(self):
        self.assertFalse(v.chars_in_list('', []))

    def test_blank_in_list_is_still_false(self):
        self.assertFalse(v.chars_in_list('', ['']))

    def test_spaces_in_list_is_still_false(self):
        self.assertFalse(v.chars_in_list(' ', [' ']))

    def test_is_digit(self):
        self.assertTrue(v.is_digit('1234'))

    def test_need_str(self):
        self.assertFalse(v.is_digit(1234))

    def test_digit_is_none(self):
        self.assertFalse(v.is_digit(None))

    def test_digit_is_spaces(self):
        self.assertFalse(v.is_digit(' '))

    def test_plus_is_still_digit(self):
        self.assertTrue(v.is_digit('+1234'))

    def test_minus_is_still_digit(self):
        self.assertTrue(v.is_digit('-1234'))

    def test_after_minus_is_not_digit(self):
        self.assertFalse(v.is_digit('-12b34'))

    def test_other_prefix_is_nor_digit(self):
        self.assertFalse(v.is_digit('*1234'))

    def test_match(self):
        self.assertTrue(v.match('hello world is here', '^.*world.*$'))

    def test_no_match(self):
        self.assertFalse(v.match('hello world is here', '^.*china.*$'))

    def test_blank_is_match(self):
        self.assertTrue(v.match('', '.*'))

    def test_not_str_is_no_match(self):
        self.assertFalse(v.match(1234, '.*'))

    def test_none_is_no_match(self):
        self.assertFalse(v.match(None, '.*'))
