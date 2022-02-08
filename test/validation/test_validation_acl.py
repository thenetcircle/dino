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
from dino.validation import AclValidator
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


class FakeDb(object):
    _admins = dict()
    _super_users = set()
    _owners = dict()

    def type_of_rooms_in_channel(self, _):
        return "temporary"

    def is_admin(self, channel_id, user_id):
        if channel_id not in FakeDb._admins:
            return False
        return user_id in FakeDb._admins[channel_id]

    def is_owner(self, room_id, user_id):
        if room_id not in FakeDb._owners:
            return False
        return user_id in FakeDb._owners[room_id]

    def is_owner_channel(self, *args):
        return False

    def is_global_moderator(self, user_id):
        return False

    def is_super_user(self, user_id):
        return user_id in FakeDb._super_users

    def channel_for_room(self, room_id):
        return BaseAclTestValidator.CHANNEL_ID

    def room_contains(self, room_id, user_id):
        return True


class BaseAclTestValidator(TestCase):
    CHANNEL_ID = '8765'
    ROOM_ID = '4567'
    USER_ID = '1234'
    USER_NAME = 'Joe'
    AGE = '30'
    GENDER = 'f'
    MEMBERSHIP = '0'
    IMAGE = 'y'
    HAS_WEBCAM = 'y'
    FAKE_CHECKED = 'n'
    COUNTRY = 'cn'
    CITY = 'Shanghai'
    TOKEN = str(uuid())

    def acls_for_room_join(self):
        return {
            'gender': 'f'
        }

    def acls_for_room_join_country(self):
        return {
            'country': 'cn,de'
        }

    def acls_for_room_message(self):
        return {
            'age': '35:'
        }

    def act(self):
        return as_parser(self.json_act())

    def json_act(self):
        return {
            'actor': {
                'id': BaseAclTestValidator.USER_ID,
                'url': BaseAclTestValidator.ROOM_ID
            },
            'provider': {
                'url': BaseAclTestValidator.CHANNEL_ID
            },
            'verb': 'join',
            'object': {
                'url': BaseAclTestValidator.CHANNEL_ID,
            },
            'target': {
                'id': BaseAclTestValidator.ROOM_ID,
                'objectType': 'room'
            }
        }

    def set_owner(self):
        FakeDb._owners[BaseAclTestValidator.ROOM_ID] = {BaseAclTestValidator.USER_ID}

    def set_admin(self):
        FakeDb._admins[BaseAclTestValidator.CHANNEL_ID] = {BaseAclTestValidator.USER_ID}

    def set_super_user(self):
        FakeDb._super_users.add(BaseAclTestValidator.USER_ID)

    def setUp(self):
        environ.env.db = FakeDb()
        self.auth = AuthRedis(host='mock', env=environ.env)
        environ.env.session = {
            SessionKeys.user_id.value: BaseAclTestValidator.USER_ID,
            SessionKeys.user_name.value: BaseAclTestValidator.USER_NAME,
            SessionKeys.age.value: BaseAclTestValidator.AGE,
            SessionKeys.gender.value: BaseAclTestValidator.GENDER,
            SessionKeys.membership.value: BaseAclTestValidator.MEMBERSHIP,
            SessionKeys.image.value: BaseAclTestValidator.IMAGE,
            SessionKeys.has_webcam.value: BaseAclTestValidator.HAS_WEBCAM,
            SessionKeys.fake_checked.value: BaseAclTestValidator.FAKE_CHECKED,
            SessionKeys.country.value: BaseAclTestValidator.COUNTRY,
            SessionKeys.city.value: BaseAclTestValidator.CITY,
            SessionKeys.token.value: BaseAclTestValidator.TOKEN
        }

        FakeDb._admins = dict()
        FakeDb._super_users = set()

        environ.env.config = {
            ConfigKeys.ACL: {
                'room': {
                    'join': {
                        'ecludes': [],
                        'acls': [
                            'gender',
                            'age',
                            'country'
                        ]
                    },
                    'message': {
                        'ecludes': [],
                        'acls': [
                            'gender',
                            'age'
                        ]
                    }
                },
                'available': {
                    'acls': [
                        'gender',
                        'age'
                    ]
                },
                'validation': {
                    'country': {
                        'type': 'anything',
                        'value': AclStrInCsvValidator()
                    },
                    'gender': {
                        'type': 'str_in_csv',
                        'value': AclStrInCsvValidator('m,f')
                    },
                    'age': {
                        'type': 'range',
                        'value': AclRangeValidator()
                    }
                }
            }
        }
        self.auth.redis.hmset(RedisKeys.auth_key(BaseAclTestValidator.USER_ID), environ.env.session)
        self.validator = AclValidator()


class TestIsAdminValidator(BaseAclTestValidator):
    def setUp(self):
        super(TestIsAdminValidator, self).setUp()

    def test_call_not_admin(self):
        validator = AclIsAdminValidator()
        is_valid, msg = validator(as_parser(self.json_act()), environ.env)
        self.assertFalse(is_valid)

    def test_call_is_admin(self):
        self.set_admin()
        validator = AclIsAdminValidator()
        is_valid, msg = validator(as_parser(self.json_act()), environ.env)
        self.assertTrue(is_valid)


class TestIsSuperUserValidator(BaseAclTestValidator):
    def setUp(self):
        super(TestIsSuperUserValidator, self).setUp()

    def test_call_not_super_user(self):
        validator = AclIsSuperUserValidator()
        is_valid, msg = validator(as_parser(self.json_act()), environ.env)
        self.assertFalse(is_valid)

    def test_call_is_super_user(self):
        self.set_super_user()
        validator = AclIsSuperUserValidator()
        is_valid, msg = validator(as_parser(self.json_act()), environ.env)
        self.assertTrue(is_valid)


class TestDisallowValidator(BaseAclTestValidator):
    def setUp(self):
        super(TestDisallowValidator, self).setUp()

    def test_call_not_super_user(self):
        validator = AclDisallowValidator()
        is_valid, msg = validator(as_parser(self.json_act()), environ.env)
        self.assertFalse(is_valid)

    def test_call_is_super_user(self):
        self.set_super_user()
        validator = AclDisallowValidator()
        is_valid, msg = validator(as_parser(self.json_act()), environ.env)
        self.assertFalse(is_valid)

    def test_new_values(self):
        validator = AclDisallowValidator()
        validator.validate_new_acl('asf')


class TestSameChannelValidator(BaseAclTestValidator):
    def setUp(self):
        super(TestSameChannelValidator, self).setUp()

    def test_call(self):
        validator = AclSameChannelValidator()
        is_valid, msg = validator(as_parser(self.json_act()), environ.env)
        self.assertTrue(is_valid)

    def test_call_not_same_channel(self):
        validator = AclSameChannelValidator()
        act = self.json_act()
        act['provider']['url'] = str(uuid())
        is_valid, msg = validator(as_parser(act), environ.env)
        self.assertFalse(is_valid)

    def test_call_blank_origin_channel(self):
        validator = AclSameChannelValidator()
        act = self.json_act()
        act['provider']['url'] = ''
        is_valid, msg = validator(as_parser(act), environ.env)
        self.assertFalse(is_valid)

    def test_call_blank_target_channel(self):
        validator = AclSameChannelValidator()
        act = self.json_act()
        act['object']['url'] = ''
        is_valid, msg = validator(as_parser(act), environ.env)
        self.assertFalse(is_valid)


class TestSameRoomValidator(BaseAclTestValidator):
    def setUp(self):
        super(TestSameRoomValidator, self).setUp()

    def test_call(self):
        validator = AclSameRoomValidator()
        is_valid, msg = validator(as_parser(self.json_act()), environ.env)
        self.assertTrue(is_valid)

    def test_call_not_same_channel(self):
        validator = AclSameRoomValidator()
        act = self.json_act()
        act['actor']['url'] = str(uuid())
        is_valid, msg = validator(as_parser(act), environ.env)
        self.assertFalse(is_valid)

    def test_call_blank_origin_room(self):
        validator = AclSameRoomValidator()
        act = self.json_act()
        act['actor']['url'] = ''
        is_valid, msg = validator(as_parser(act), environ.env)
        self.assertFalse(is_valid)

    def test_call_blank_target_room(self):
        validator = AclSameRoomValidator()
        act = self.json_act()
        act['target']['id'] = ''
        is_valid, msg = validator(as_parser(act), environ.env)
        self.assertFalse(is_valid)

    def test_new_vals(self):
        validator = AclSameRoomValidator()
        validator.validate_new_acl('asf')


class TestAclStrInCsvValidator(BaseAclTestValidator):
    def setUp(self):
        super(TestAclStrInCsvValidator, self).setUp()

    def test_call(self):
        validator = AclStrInCsvValidator()
        is_valid, msg = validator(as_parser(self.json_act()), environ.env, 'gender', 'm,f')
        self.assertTrue(is_valid)

    def test_call_blank_values(self):
        validator = AclStrInCsvValidator()
        is_valid, msg = validator(as_parser(self.json_act()), environ.env, 'gender', '')
        self.assertTrue(is_valid)

    def test_call_not_in_session(self):
        validator = AclStrInCsvValidator()
        is_valid, msg = validator(as_parser(self.json_act()), environ.env, 'other-stuff', 'a,b,c')
        self.assertFalse(is_valid)

    def test_validate_new_acl_blank(self):
        AclStrInCsvValidator('a,b,c').validate_new_acl('')


class TestAclRangeValidator(BaseAclTestValidator):
    def setUp(self):
        super(TestAclRangeValidator, self).setUp()

    def test_call(self):
        validator = AclRangeValidator()
        is_valid, msg = validator(as_parser(self.json_act()), environ.env, 'age', '25:50')
        self.assertTrue(is_valid)

    def test_call_no_end(self):
        validator = AclRangeValidator()
        is_valid, msg = validator(as_parser(self.json_act()), environ.env, 'age', '25:')
        self.assertTrue(is_valid)

    def test_call_no_beginning(self):
        validator = AclRangeValidator()
        is_valid, msg = validator(as_parser(self.json_act()), environ.env, 'age', ':50')
        self.assertTrue(is_valid)

    def test_call_blank_values(self):
        validator = AclRangeValidator()
        is_valid, msg = validator(as_parser(self.json_act()), environ.env, 'age', '')
        self.assertFalse(is_valid)

    def test_call_not_in_session(self):
        validator = AclRangeValidator()
        is_valid, msg = validator(as_parser(self.json_act()), environ.env, 'other-stuff', '')
        self.assertFalse(is_valid)

    def test_call_blank_in_session(self):
        validator = AclRangeValidator()
        environ.env.session[SessionKeys.age.value] = ''
        is_valid, msg = validator(as_parser(self.json_act()), environ.env, 'age', ':50')
        self.assertFalse(is_valid)

    def test_call_session_value_invalid(self):
        environ.env.session[SessionKeys.age.value] = 'k'
        validator = AclRangeValidator()
        is_valid, msg = validator(as_parser(self.json_act()), environ.env, 'age', ':50')
        self.assertFalse(is_valid)

    def test_call_new_vals_blank_values(self):
        validator = AclRangeValidator()
        self.assertRaises(ValidationException, validator.validate_new_acl, '')

    def test_call_new_vals_no_range(self):
        validator = AclRangeValidator()
        self.assertRaises(ValidationException, validator.validate_new_acl, '25')

    def test_call_new_vals(self):
        AclRangeValidator().validate_new_acl('25:50')

    def test_call_new_vals_invalid_end(self):
        validator = AclRangeValidator()
        self.assertRaises(ValidationException, validator.validate_new_acl, '25:a')

    def test_call_new_vals_invalid_beginning(self):
        validator = AclRangeValidator()
        self.assertRaises(ValidationException, validator.validate_new_acl, 'a:25')

    def test_call_new_vals_no_end(self):
        AclRangeValidator().validate_new_acl('25:')

    def test_call_new_vals_no_beginning(self):
        AclRangeValidator().validate_new_acl(':25')

    def test_call_new_vals_no_limit(self):
        AclRangeValidator().validate_new_acl(':')


class TestAclConfigRootsValidator(BaseAclTestValidator):
    def setUp(self):
        super(TestAclConfigRootsValidator, self).setUp()

    def test_check_acl_roots(self):
        AclConfigValidator.check_acl_roots({
            'available': {
                'acls': []
            },
            'room': {
                'acls': []
            },
            'channel': {
                'acls': []
            },
            'validation': {
            },
        })

    def test_check_acl_roots_no_available(self):
        acls = {
            'room': {
                'acls': []
            },
            'channel': {
                'acls': []
            },
            'validation': {
            },
        }
        self.assertRaises(RuntimeError, AclConfigValidator.check_acl_roots, acls)

    def test_check_acl_roots_unknown_root(self):
        acls = {
            'available': {
                'acls': []
            },
            'what-is-this': {
                'acls': []
            },
            'channel': {
                'acls': []
            },
            'validation': {
            },
        }
        self.assertRaises(RuntimeError, AclConfigValidator.check_acl_roots, acls)

    def test_check_acl_roots_no_acls_in_available(self):
        acls = {
            'available': {
                'foo': []
            },
            'room': {
                'acls': []
            },
            'channel': {
                'acls': []
            },
            'validation': {
            },
        }
        self.assertRaises(RuntimeError, AclConfigValidator.check_acl_roots, acls)


class TestAclConfigValidationMethodsValidator(BaseAclTestValidator):
    def setUp(self):
        super(TestAclConfigValidationMethodsValidator, self).setUp()

    def test_empty_methods(self):
        acls = {
            'available': {'acls': []},
            'validation': {},
        }
        AclConfigValidator.check_acl_validation_methods(acls, acls['available']['acls'])

    def test_str_in_csv_method(self):
        acls = {
            'available': {'acls': ['gender']},
            'validation': {'gender': {
                'type': 'str_in_csv',
                'value': 'm,f'
            }},
        }
        AclConfigValidator.check_acl_validation_methods(acls, acls['available']['acls'])

    def test_anything_but_with_value(self):
        acls = {
            'available': {'acls': ['gender']},
            'validation': {'gender': {
                'type': 'anything',
                'value': 'm,f'
            }},
        }
        AclConfigValidator.check_acl_validation_methods(acls, acls['available']['acls'])

    def test_invalid_method(self):
        acls = {
            'available': {'acls': ['gender']},
            'validation': {'foo': {
                'type': 'str_in_csv',
                'value': 'm,f'
            }},
        }
        self.assertRaises(RuntimeError, AclConfigValidator.check_acl_validation_methods, acls, acls['available']['acls'])

    def test_missing_type(self):
        acls = {
            'available': {'acls': ['gender']},
            'validation': {'gender': {
                'value': 'm,f'
            }},
        }
        self.assertRaises(RuntimeError, AclConfigValidator.check_acl_validation_methods, acls, acls['available']['acls'])

    def test_invalid_type(self):
        acls = {
            'available': {'acls': ['gender']},
            'validation': {'gender': {
                'type': 'foo',
                'value': 'm,f'
            }},
        }
        self.assertRaises(RuntimeError, AclConfigValidator.check_acl_validation_methods, acls, acls['available']['acls'])

    def test_blank_value_with_str_in_csv_method(self):
        acls = {
            'available': {'acls': ['gender']},
            'validation': {'gender': {
                'type': 'str_in_csv',
                'value': ''
            }},
        }
        self.assertRaises(RuntimeError, AclConfigValidator.check_acl_validation_methods, acls, acls['available']['acls'])


class TestKeysInAvailableValidator(BaseAclTestValidator):
    def setUp(self):
        super(TestKeysInAvailableValidator, self).setUp()
        self.available = ['gender', 'membership', 'age']

    def test_in_types(self):
        keys = {'gender', 'membership'}
        AclConfigValidator.check_acl_keys_in_available(self.available, ApiTargets.ROOM, keys)

    def test_invalid_type(self):
        keys = {'gender', 'foo'}
        self.assertRaises(RuntimeError, AclConfigValidator.check_acl_keys_in_available, self.available, ApiTargets.ROOM, keys)


class TestAclConfigExcludeValidator(BaseAclTestValidator):
    def setUp(self):
        super(TestAclConfigExcludeValidator, self).setUp()

    def test_exclude_existing(self):
        AclConfigValidator.check_acl_excludes(['foo', 'bar', 'baz'], ['foo', 'bar'])

    def test_exclude_nothing(self):
        AclConfigValidator.check_acl_excludes(['foo', 'bar', 'baz'], [])

    def test_exclude_nothing_and_no_available(self):
        AclConfigValidator.check_acl_excludes([], [])

    def test_exclude_unavailable(self):
        self.assertRaises(RuntimeError, AclConfigValidator.check_acl_excludes, ['foo', 'bar'], ['baz'])


class TestAclRulesValidator(BaseAclTestValidator):
    def setUp(self):
        super(TestAclRulesValidator, self).setUp()
        self.rules = ['acls', 'exclude']
        self.actions = {
            'room': ['foo', 'bar'],
            'channel': ['baz']
        }

    def test_rules(self):
        acls = {
            'room': {
                'gender': {
                    'acls': [],
                    'exclude': []
                }
            }
        }
        AclConfigValidator.check_acl_rules(acls, self.actions, self.rules)

    def test_invalid_rule(self):
        acls = {
            'room': {
                'gender': {
                    'foo': [],
                    'exclude': []
                }
            }
        }
        self.assertRaises(RuntimeError, AclConfigValidator.check_acl_rules, acls, self.actions, self.rules)

    def test_ignore_unknown_actions(self):
        acls = {
            'foo': {
                'bar': {
                    'acls': [],
                    'exclude': []
                }
            }
        }
        AclConfigValidator.check_acl_rules(acls, self.actions, self.rules)

    def test_action_is_none(self):
        acls = {
            'foo': {
                'bar': None
            }
        }
        AclConfigValidator.check_acl_rules(acls, self.actions, self.rules)


class TestCheckAclActionsValidator(BaseAclTestValidator):
    def setUp(self):
        super(TestCheckAclActionsValidator, self).setUp()
        self.rules = ['acls', 'exclude']
        self.available = ['foo', 'bar', 'baz']
        self.actions = {
            'room': ['join', 'kick'],
            'channel': ['create']
        }

    def test_actions(self):
        acls = {
            'room': {
                'join': {
                    'acls': [],
                    'exclude': []
                }
            }
        }
        check_acls = [
            ('channel', acls.get('channel', None)),
            ('room', acls.get('room', None))
        ]
        AclConfigValidator.check_acl_actions(check_acls, self.actions, self.available)

    def test_action_is_none(self):
        acls = {
            'room': {
                'join': None
            }
        }
        check_acls = [
            ('channel', acls.get('channel', None)),
            ('room', acls.get('room', None))
        ]
        AclConfigValidator.check_acl_actions(check_acls, self.actions, self.available)

    def test_empty_acl(self):
        acls = {
            'room': {
                'join': None
            }
        }
        check_acls = [
            ('channel', []),
            ('room', acls.get('room', None))
        ]
        AclConfigValidator.check_acl_actions(check_acls, self.actions, self.available)

    def test_invalid_action(self):
        acls = {
            'room': {
                'foo': {
                    'acls': [],
                    'exclude': []
                }
            }
        }
        check_acls = [
            ('channel', acls.get('channel', None)),
            ('room', acls.get('room', None))
        ]
        self.assertRaises(RuntimeError, AclConfigValidator.check_acl_actions, check_acls, self.actions, self.available)

    def test_no_acls_for_action(self):
        acls = {
            'room': {
                'join': {
                    'exclude': []
                }
            }
        }
        check_acls = [
            ('channel', acls.get('channel', None)),
            ('room', acls.get('room', None))
        ]
        AclConfigValidator.check_acl_actions(check_acls, self.actions, self.available)

    def test_acls_not_dict(self):
        acls = {
            'room': {
                'join': []
            }
        }
        check_acls = [
            ('channel', acls.get('channel', None)),
            ('room', acls.get('room', None))
        ]
        self.assertRaises(RuntimeError, AclConfigValidator.check_acl_actions, check_acls, self.actions, self.available)


class TestIsAclValid(BaseAclTestValidator):
    def setUp(self):
        super(TestIsAclValid, self).setUp()

    def test_invalid_value(self):
        is_valid, _ = self.validator.is_acl_valid('gender', 'h')
        self.assertFalse(is_valid)

    def test_valid_value(self):
        is_valid, _ = self.validator.is_acl_valid('gender', 'm')
        self.assertTrue(is_valid)

    def test_invalid_type(self):
        is_valid, _ = self.validator.is_acl_valid('something-invalid', 'm')
        self.assertFalse(is_valid)

    def test_blank_value(self):
        is_valid, _ = self.validator.is_acl_valid('gender', '')
        self.assertTrue(is_valid)

    def test_invalid_validator_class(self):
        class FakeValidator(object):
            pass

        new_acls = environ.env.config.get(ConfigKeys.ACL)
        new_acls['validation']['age']['value'] = FakeValidator()
        environ.env.config = {ConfigKeys.ACL: new_acls}
        is_valid, _ = self.validator.is_acl_valid('age', '28:35')
        self.assertFalse(is_valid)


class TestAclValidator(BaseAclTestValidator):
    def setUp(self):
        super(TestAclValidator, self).setUp()

    def test_validate_acl_for_action_no_target(self):
        act = self.json_act()
        del act['target']
        is_valid, msg = self.validator.validate_acl_for_action(
                as_parser(act), 'room', 'join', self.acls_for_room_join())
        self.assertFalse(is_valid)

    def test_validate_acl_for_action_no_target_object_type(self):
        act = self.json_act()
        del act['target']['objectType']
        is_valid, msg = self.validator.validate_acl_for_action(
                as_parser(act), 'room', 'join', self.acls_for_room_join())
        self.assertFalse(is_valid)

    def test_validate_acl_for_action_blank_target_object_type(self):
        act = self.json_act()
        act['target']['objectType'] = ''
        is_valid, msg = self.validator.validate_acl_for_action(
                as_parser(act), 'room', 'join', self.acls_for_room_join())
        self.assertFalse(is_valid)

    def test_validate_acl_for_action_unknown_target(self):
        act = self.json_act()
        is_valid, msg = self.validator.validate_acl_for_action(
                as_parser(act), 'other-target', 'join', self.acls_for_room_join())
        self.assertTrue(is_valid)

    def test_validate_acl_for_action_private_chat_ignores_wrong_gender(self):
        environ.env.session[SessionKeys.gender.value] = 'k'
        act = self.json_act()
        act['target']['objectType'] = 'private'
        is_valid, msg = self.validator.validate_acl_for_action(
                as_parser(act), 'room', 'join', self.acls_for_room_join())
        self.assertTrue(is_valid)

    def test_validate_acl_for_action_non_private_does_not_ignore_wrong_gender(self):
        environ.env.session[SessionKeys.gender.value] = 'k'
        act = self.json_act()
        is_valid, msg = self.validator.validate_acl_for_action(
                as_parser(act), 'room', 'join', self.acls_for_room_join())
        self.assertFalse(is_valid)

    def test_validate_acl_for_action_admin_ignores(self):
        environ.env.session[SessionKeys.gender.value] = 'k'
        self.set_admin()
        act = self.json_act()
        is_valid, msg = self.validator.validate_acl_for_action(
                as_parser(act), 'room', 'join', self.acls_for_room_join())
        self.assertTrue(is_valid)

    def test_validate_acl_for_action_super_user_ignores(self):
        environ.env.session[SessionKeys.gender.value] = 'k'
        self.set_super_user()
        act = self.json_act()
        is_valid, msg = self.validator.validate_acl_for_action(
                as_parser(act), 'room', 'join', self.acls_for_room_join())
        self.assertTrue(is_valid)

    def test_validate_acl_for_action_owner_ignores(self):
        environ.env.session[SessionKeys.gender.value] = 'k'
        self.set_owner()
        act = self.json_act()
        is_valid, msg = self.validator.validate_acl_for_action(
                as_parser(act), 'room', 'join', self.acls_for_room_join())
        self.assertTrue(is_valid)

    def test_validate_acl_for_action_join(self):
        is_valid, msg = self.validator.validate_acl_for_action(
                self.act(), 'room', 'join', self.acls_for_room_join())
        self.assertTrue(is_valid)

    def test_is_acl_valid_invalid_type(self):
        is_valid, msg = self.validator.validate_acl_for_action(
                self.act(), 'room', 'join', self.acls_for_room_join())
        self.assertTrue(is_valid)

    def test_validate_acl_for_action_join_country(self):
        is_valid, msg = self.validator.validate_acl_for_action(
                self.act(), 'room', 'join', self.acls_for_room_join_country())
        self.assertTrue(is_valid)

    def test_validate_acl_for_action_join_wrong_country(self):
        environ.env.session[SessionKeys.country.value] = 'xx'
        is_valid, msg = self.validator.validate_acl_for_action(
                self.act(), 'room', 'join', self.acls_for_room_join_country())
        self.assertFalse(is_valid)

    def test_validate_acl_for_action_join_wrong_gender(self):
        environ.env.session[SessionKeys.gender.value] = 'm'
        is_valid, msg = self.validator.validate_acl_for_action(
                self.act(), 'room', 'join', self.acls_for_room_join())
        self.assertFalse(is_valid)

    def test_validate_acl_for_action_message_too_young(self):
        is_valid, msg = self.validator.validate_acl_for_action(
                self.act(), 'room', 'message', self.acls_for_room_message())
        self.assertFalse(is_valid)

    def test_validate_acl_for_action_message_crossroom_same_channel(self):
        json_act = self.json_act()
        other_room_id = str(uuid())
        json_act['actor']['url'] = other_room_id
        is_valid, msg = self.validator.validate_acl_for_action(
                self.act(), 'room', 'message', self.acls_for_room_message())
        self.assertFalse(is_valid)


class BaseAclTestValidatorTest(TestCase):
    def test_is_not_implemented(self):
        validator = BaseAclValidator()
        self.assertRaises(NotImplementedError, validator.validate_new_acl, 'asdf')
