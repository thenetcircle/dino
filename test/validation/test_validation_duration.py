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

from dino.validation.duration import DurationValidator

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class DurationValidatorTest(TestCase):
    def test_none(self):
        self.assertRaises(ValueError, DurationValidator, None)

    def test_blank(self):
        self.assertRaises(ValueError, DurationValidator, '')

    def test_seconds(self):
        DurationValidator('5s')

    def test_minutes(self):
        DurationValidator('5m')

    def test_hours(self):
        DurationValidator('5h')

    def test_days(self):
        DurationValidator('5d')

    def test_positive_seconds(self):
        DurationValidator('+5s')

    def test_positive_minutes(self):
        DurationValidator('+5m')

    def test_positive_hours(self):
        DurationValidator('+5h')

    def test_positive_days(self):
        DurationValidator('+5d')

    def test_negative_is_invalid(self):
        self.assertRaises(ValueError, DurationValidator, '-5m')

    def test_invalid_sufix(self):
        self.assertRaises(ValueError, DurationValidator, '5y')

    def test_invalid_number_after_plus(self):
        self.assertRaises(ValueError, DurationValidator, '+km')

    def test_invalid_suffix_after_plus(self):
        self.assertRaises(ValueError, DurationValidator, '+5y')
