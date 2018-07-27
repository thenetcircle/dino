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

from dino.validation.generic import GenericValidator

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class DurationValidator(object):
    durations = {
        'd': 'days',
        'h': 'hours',
        'm': 'minutes',
        's': 'seconds'
    }
    durations_help = ', '.join('%s (%s)' % (unit, human) for unit, human in durations.items())

    def __init__(self, ban_duration):
        if ban_duration is None or ban_duration == '':
            raise ValueError('empty ban duration')

        valid_ends = {'s', 'm', 'h', 'd'}
        if ban_duration[-1] not in valid_ends:
            raise ValueError('invalid ban duration: %s' % ban_duration)

        if ban_duration.startswith('-'):
            raise ValueError('can not set negative ban duration: %s' % ban_duration)

        if ban_duration.startswith('+'):
            ban_duration = ban_duration[1:]

        if not GenericValidator.is_digit(ban_duration[:-1]):
            raise ValueError('invalid ban duration, not a number: %s' % ban_duration)
