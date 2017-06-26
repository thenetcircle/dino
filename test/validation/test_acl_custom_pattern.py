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

from activitystreams import parse as as_parser

from unittest import TestCase
from uuid import uuid4 as uuid

from dino import environ
from dino.auth.redis import AuthRedis
from dino.config import ConfigKeys
from dino.config import SessionKeys
from dino.config import RedisKeys
from dino.config import ApiTargets
from dino.exceptions import ValidationException
from dino.validation.acl import AclPatternValidator
from dino.validation.acl import AclStrInCsvValidator
from dino.validation.acl import AclRangeValidator
from dino.validation.acl import AclIsAdminValidator
from dino.validation.acl import AclIsSuperUserValidator
from dino.validation.acl import AclDisallowValidator
from dino.validation.acl import AclSameRoomValidator
from dino.validation.acl import AclSameChannelValidator
from dino.validation.acl import AclConfigValidator
from dino.validation.acl import BaseAclValidator

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class CustomPatternAclValidator(TestCase):
    def setUp(self):
        environ.env.config = {
            ConfigKeys.ACL: {
                'room': {
                    'join': {
                    },
                    'message': {
                    }
                },
                'available': {
                },
                'validation': {
                }
            }
        }
        environ.env.config = {
            ConfigKeys.ACL: {
                'room': {
                    'join': {
                        'excludes': [],
                        'acls': [
                            'gender',
                            'age',
                            'country'
                        ]
                    },
                    'message': {
                        'excludes': [],
                        'acls': [
                            'gender',
                            'age'
                        ]
                    }
                },
                'available': {
                    'acls': [
                        'gender',
                        'age',
                        'custom',
                        'membership'
                    ]
                },
                'validation': {
                    'gender': {
                        'type': 'str_in_csv',
                        'value': AclStrInCsvValidator('m,f,ts')
                    },
                    'membership': {
                        'type': 'str_in_csv',
                        'value': AclStrInCsvValidator('normal,tg,tg-p')
                    },
                    'custom': {
                        'type': 'accepted_pattern',
                        'value': AclPatternValidator('^[0-9a-z!\|,\(\):=-]*$')
                    },
                    'age': {
                        'type': 'range',
                        'value': AclRangeValidator()
                    }
                }
            }
        }
        self.validator = AclPatternValidator('^[0-9a-z!\|,\(\):=-]*$')

    def test_pattern(self):
        self.validator.validate_new_acl('gender=m,(membership=tg-p|membership=tg),(age=34:40|age=21:25)')
