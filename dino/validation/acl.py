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

from activitystreams.models.activity import Activity

from dino.validation.generic import GenericValidator
from dino.exceptions import ValidationException
from dino.config import SessionKeys
from dino.config import ConfigKeys
from dino import environ
from dino import utils

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


class AclValidator(object):
    @staticmethod
    def _age(val: str):
        start, end = None, None

        if val is None or not isinstance(val, str) or len(val.strip()) < 2:
            return False

        val = val.strip()

        if len(val) > 1 and val.endswith(':'):
            start = val[:-1]
        elif len(val) > 1 and val.startswith(':'):
            end = val[1:]
        elif len(val.split(':')) == 2:
            start, end = val.split(':')
        else:
            return False

        if start is not None and (not GenericValidator.is_digit(start) or int(start) < 0):
            return False
        if end is not None and (not GenericValidator.is_digit(end) or int(end) < 0):
            return False

        if start is not None and end is not None and int(start) > int(end):
            return False

        return True

    @staticmethod
    def _age_range_validate(expected: str, actual: str):
        def _split_age(age_range: str):
            if len(age_range) > 1 and age_range.endswith(':'):
                return age_range[:-1], None
            elif len(age_range) > 1 and age_range.startswith(':'):
                return None, age_range[1:]
            elif len(age_range.split(':')) == 2:
                return age_range.split(':')
            else:
                return None, None

        if expected != '' and not AclValidator._age(expected) or not GenericValidator.is_digit(actual):
            return False

        expected_start, expected_end = _split_age(expected.strip())

        if expected_start is None and expected_end is None:
            return True

        if expected_start is not None and expected_start > actual:
            return False

        if expected_end is not None and expected_end < actual:
            return False

        return True

    @staticmethod
    def _true_false_all(val: str):
        return val in ['y', 'n', 'a']

    @staticmethod
    def generic_validator(expected, actual):
        return expected is None or actual in expected.split(',')

    ACL_MATCHERS = {
        SessionKeys.age.value:
            lambda expected, actual: expected is None or AclValidator._age_range_validate(expected, actual),

        SessionKeys.gender.value:
            lambda expected, actual: AclValidator.generic_validator(expected, actual),

        SessionKeys.membership.value:
            lambda expected, actual: AclValidator.generic_validator(expected, actual),

        SessionKeys.group.value:
            lambda expected, actual: AclValidator.generic_validator(expected, actual),

        SessionKeys.country.value:
            lambda expected, actual: AclValidator.generic_validator(expected, actual),

        SessionKeys.city.value:
            lambda expected, actual: AclValidator.generic_validator(expected, actual),

        SessionKeys.image.value:
            lambda expected, actual: AclValidator.generic_validator(expected, actual),

        SessionKeys.has_webcam.value:
            lambda expected, actual: AclValidator.generic_validator(expected, actual),

        SessionKeys.fake_checked.value:
            lambda expected, actual: AclValidator.generic_validator(expected, actual)
    }

    # TODO: use ValidationKeys instead of SessionKeys
    ACL_VALIDATORS = {
        SessionKeys.gender.value:
            lambda v: v is None or GenericValidator.chars_in_list(v, ['m', 'f', 'ts']),

        SessionKeys.membership.value:
            lambda v: v is None or GenericValidator.chars_in_list(v, ['0', '1', '2', '3', '4']),

        SessionKeys.age.value:
            lambda v: v is None or AclValidator._age(v),

        # 2 character country codes, no spaces
        SessionKeys.country.value:
            lambda v: v is None or GenericValidator.match(v, '^([A-Za-z]{2},)*([A-Za-z]{2})+$'),

        # city names can have spaces and dashes in them
        SessionKeys.city.value:
            lambda v: v is None or GenericValidator.match(v, '^([\w -]+,)*([\w -]+)+$'),

        SessionKeys.image.value:
            lambda v: v is None or AclValidator._true_false_all(v),

        SessionKeys.crossgroup.value:
            lambda v: v is None or AclValidator._true_false_all(v),

        SessionKeys.group.value:
            lambda v: v is None or GenericValidator.is_string(v) and len(v) > 0,

        'user_id':
            lambda v: GenericValidator.is_digit(v),

        'user_name':
            lambda v: GenericValidator.is_string(v) and len(v) > 0,

        'token':
            lambda v: GenericValidator.is_string(v) and len(v) > 0,

        SessionKeys.has_webcam.value:
            lambda v: v is None or AclValidator._true_false_all(v),

        SessionKeys.fake_checked.value:
            lambda v: v is None or AclValidator._true_false_all(v),
    }

    def is_acl_valid(self, acl_type, acl_value):
        validator = AclValidator.ACL_VALIDATORS.get(acl_type, None)
        if validator is None:
            return False
        if not callable(validator):
            return False
        return validator(acl_value)

    def validate_acl_for_action(self, activity: Activity, target: str, action: str, target_acls: dict) -> (bool, str):
        all_acls = environ.env.config.get(ConfigKeys.ACL)

        if target == 'room' and activity.target.object_type != 'group':
            return True, None

        user_id = activity.actor.id
        channel_id = activity.object.url

        # no acls for this target (room/channel) and action (join/kick/etc)
        if target not in all_acls or action not in all_acls[target] or len(all_acls[target][action]) == 0:
            return False, 'no acl set that allows action "%s" for target type "%s"'

        if utils.is_admin(channel_id, user_id):
            return True, None
        if utils.is_owner_channel(channel_id, user_id):
            return True, None
        if utils.is_super_user(user_id):
            return True, None

        if target == 'channel':
            pass
        elif target == 'room':
            room_id = activity.target.id
            if utils.is_owner(room_id, user_id):
                return True, None
        else:
            return False, 'unknown target "%s", must be one of [channel, room]' % target

        # no acls for this target and action
        if target_acls is None or len(target_acls) == 0:
            return True, None

        possible_acls = all_acls[target][action]
        for acl_rule, acl_values in possible_acls.items():
            if acl_rule != 'acls':
                continue

            for acl in acl_values:
                if acl not in target_acls.keys():
                    continue

                is_valid_func = all_acls['validation'][acl]['value']
                is_valid, msg = is_valid_func(activity, environ.env, acl, target_acls[acl])
                if not is_valid:
                    logger.info(
                            'acl "%s" did not validate for target acl "%s": %s' %
                            (acl, target_acls[acl], msg))
                    return False, 'acl "%s" did not validate for target acl "%s": %s' % (
                        acl, target_acls[acl], msg)

        return True, None

    def validate_acl(self, activity: Activity) -> (bool, str):
        room_id = activity.target.id
        room_name = utils.get_room_name(room_id)
        user_id = environ.env.session.get('user_id', 'NOT_FOUND_IN_SESSION')
        user_name = environ.env.session.get('user_name', 'NOT_FOUND_IN_SESSION')
        channel_id = utils.get_channel_for_room(room_id)

        # owners can always join
        # todo: maybe not if banned? or remove owner status if banned?
        if utils.is_owner(room_id, user_id):
            _msg = 'user %s (%s) is an owner of room %s (%s), skipping ACL validation'
            environ.env.logger.debug(_msg % (user_id, user_name, room_id, room_name))
            return True, None
        if utils.is_admin(channel_id, user_id):
            _msg = 'user %s (%s) is an admin of channel %s, skipping ACL validation'
            environ.env.logger.debug(_msg % (user_id, user_name, channel_id))
            return True, None
        if utils.is_owner_channel(channel_id, user_id):
            _msg = 'user %s (%s) is an owner of the channel for room %s (%s), skipping ACL validation'
            environ.env.logger.debug(_msg % (user_id, user_name, room_id, room_name))
            return True, None
        if utils.is_super_user(user_id):
            _msg = 'user %s (%s) is a super user, skipping ACL validation'
            environ.env.logger.debug(_msg % (user_id, user_name))
            return True, None

        room_acls = environ.env.db.get_acls(room_id)
        channel_acls = environ.env.db.get_acls_channel(channel_id)
        if len(channel_acls) == 0 and len(room_acls) == 0:
            return True, None

        all_acls = [room_acls, channel_acls]

        for acls in all_acls:
            for acl_key, acl_val in acls.items():
                if acl_key not in environ.env.session:
                    error_msg = 'Key "%s" not in session for user, cannot let "%s" (%s) join "%s" (%s)'
                    error_msg %= (acl_key, user_id, user_name, room_id, room_name)
                    environ.env.logger.error(error_msg)
                    return False, error_msg

                session_value = environ.env.session.get(acl_key, None)
                if session_value is None:
                    error_msg = 'Value for key "%s" not in session, cannot let "%s" (%s) join "%s" (%s)'
                    error_msg %= (acl_key, user_id, user_name, room_id, room_name)
                    environ.env.logger.error(error_msg)
                    return False, error_msg

                if acl_key not in AclValidator.ACL_MATCHERS:
                    error_msg = 'No validator for ACL type "%s", cannot let "%s" (%s) join "%s" (%s)'
                    error_msg %= (acl_key, user_id, user_name, room_id, room_name)
                    environ.env.logger.error(error_msg)
                    return False, error_msg

                validator = AclValidator.ACL_MATCHERS[acl_key]
                if not callable(validator):
                    error_msg = 'Validator for ACL type "%s" is not callable, cannot let "%s" (%s) join "%s" (%s)'
                    error_msg %= (acl_key, user_id, user_name, room_id, room_name)
                    environ.env.logger.error(error_msg)
                    return False, error_msg

                if not validator(acl_val, session_value):
                    error_msg = 'Value "%s" not valid for ACL "%s" (value "%s"), cannot let "%s" (%s) join "%s" (%s)'
                    error_msg %= (session_value, acl_key, acl_val, user_id, user_name, room_id, room_name)
                    environ.env.logger.info(error_msg)
                    return False, error_msg

        return True, None

    def validate_acl_channel(self, activity: Activity) -> (bool, str):
        channel_id = activity.object.url
        user_id = environ.env.session.get('user_id', 'NOT_FOUND_IN_SESSION')
        user_name = environ.env.session.get('user_name', 'NOT_FOUND_IN_SESSION')

        # owners can always join
        # todo: maybe not if banned? or remove owner status if banned?
        if utils.is_owner_channel(channel_id, user_id):
            _msg = 'user %s (%s) is an owner of channel %s, skipping ACL validation'
            environ.env.logger.debug(_msg % (user_id, user_name, channel_id))
            return True, None
        if utils.is_admin(channel_id, user_id):
            _msg = 'user %s (%s) is an admin of channel %s, skipping ACL validation'
            environ.env.logger.debug(_msg % (user_id, user_name, channel_id))
            return True, None
        if utils.is_super_user(user_id):
            _msg = 'user %s (%s) is a super user, skipping ACL validation'
            environ.env.logger.debug(_msg % (user_id, user_name))
            return True, None

        acls = environ.env.db.get_acls_channel(channel_id)
        if len(acls) == 0:
            return True, None

        for acl_key, acl_val in acls.items():
            if acl_key not in environ.env.session:
                error_msg = 'Key "%s" not in session for user, cannot let "%s" (%s) join channel "%s"'
                error_msg %= (acl_key, user_id, user_name, channel_id)
                environ.env.logger.error(error_msg)
                return False, error_msg

            session_value = environ.env.session.get(acl_key, None)
            if session_value is None:
                error_msg = 'Value for key "%s" not in session, cannot let "%s" (%s) join channel "%s"'
                error_msg %= (acl_key, user_id, user_name, channel_id)
                environ.env.logger.error(error_msg)
                return False, error_msg

            if acl_key not in AclValidator.ACL_MATCHERS:
                error_msg = 'No validator for ACL type "%s", cannot let "%s" (%s) join join channel "%s"'
                error_msg %= (acl_key, user_id, user_name, channel_id)
                environ.env.logger.error(error_msg)
                return False, error_msg

            validator = AclValidator.ACL_MATCHERS[acl_key]
            if not callable(validator):
                error_msg = 'Validator for ACL type "%s" is not callable, cannot let "%s" (%s) join channel "%s"'
                error_msg %= (acl_key, user_id, user_name, channel_id)
                environ.env.logger.error(error_msg)
                return False, error_msg

            if not validator(acl_val, session_value):
                error_msg = 'Value "%s" not valid for ACL "%s" (value "%s"), cannot let "%s" (%s) join channel "%s"'
                error_msg %= (session_value, acl_key, acl_val, user_id, user_name, channel_id)
                environ.env.logger.info(error_msg)
                return False, error_msg

        return True, None


class BaseAclValidator(object):
    def validate_new_acl(self, values):
        raise NotImplementedError('validate_new_acl')


class AclDisallowValidator(BaseAclValidator):
    def __init__(self):
        pass

    def validate_new_acl(self, values):
        pass

    def __call__(self, *args, **kwargs):
        return False, 'not allowed'


class AclSameChannelValidator(BaseAclValidator):
    def __init__(self):
        pass

    def validate_new_acl(self, values):
        pass

    def __call__(self, *args, **kwargs):
        activity = args[0]
        # env = args[1]
        # acl_type = args[2]
        # acl_values = args[3]

        origin_channel_id = activity.actor.url
        if origin_channel_id is None or len(origin_channel_id.strip()) == 0:
            return False, 'no origin channel uuid in actor.url'

        target_channel_id = activity.object.url
        if target_channel_id is None or len(target_channel_id.strip()) == 0:
            return False, 'no target channel uuid in object.url'

        if origin_channel_id == target_channel_id:
            return True, None
        return False, 'channels are not the same'


class AclStrInCsvValidator(BaseAclValidator):
    def __init__(self, csv=None):
        self.valid_csvs = None
        if csv is not None:
            self.valid_csvs = csv.split(',')

    def validate_new_acl(self, values):
        # all new values accepted, e.g. for city or country
        if self.valid_csvs is None:
            return

        if values is None or len(values.strip()) == 0:
            return

        new_values = values.split(',')
        for new_value in new_values:
            if new_value in self.valid_csvs:
                continue

            raise ValidationException(
                    'new acl values "%s" does not match configured possible values "%s"' %
                    (values, self.valid_csvs))

    def __call__(self, *args, **kwargs):
        # activity = args[0]
        env = args[1]
        acl_type = args[2]
        acl_values = args[3]

        if acl_values.strip() == '':
            return True
        acl_values = acl_values.split(',')

        session_value = env.session.get(acl_type)
        if session_value is None or session_value not in acl_values:
            logger.warning('no session value for acl "%s"' % acl_type)
            return False, 'no session value for acl"%s"' % acl_type

        return True, None


class AclRangeValidator(BaseAclValidator):
    def __init__(self):
        pass

    def validate_new_acl(self, values):
        if values is None or len(values.strip()) == 0:
            raise ValidationException('blank range when creating AclRangeValidator')

        if ':' not in values:
            raise ValidationException('value not a range, no colon in value: "%s"' % values)

        range_min, range_max = values.split(':', 1)
        if range_min != '':
            if not GenericValidator.is_digit(range_min):
                raise ValidationException('first value in range "%s" is not a number' % values)
        if range_max != '':
            if not GenericValidator.is_digit(range_max):
                raise ValidationException('last value in range "%s" is not a number' % values)

    def __call__(self, *args, **kwargs):
        # activity = args[0]
        env = args[1]
        acl_type = args[2]
        acl_range = args[3]

        session_value = env.session.get(acl_type)

        if acl_range is None or len(acl_range.strip()) == 0:
            return False, 'blank range when creating AclRangeValidator'

        range_min, range_max = acl_range.split(':', 1)

        if range_min == '':
            range_min = None
        else:
            range_min = int(range_min)

        if range_max == '':
            range_max = None
        else:
            range_max = int(range_max)

        if session_value is None or len(session_value.strip()) == 0:
            return False, 'blank value in AclRangeValidator'

        try:
            value = int(session_value)
        except ValueError:
            return False, 'session value "%s" is not a valid number' % session_value

        if range_min is not None and range_min > value:
            return False
        if range_max is not None and range_max < value:
            return False
        return True


class AclConfigValidator(object):
    @staticmethod
    def check_acl_roots(acls: dict) -> None:
        valid_roots = ['validation', 'room', 'available', 'channel']
        if 'available' not in acls.keys():
            raise RuntimeError('no ACLs in root "available"')
        if 'acls' not in acls['available']:
            raise RuntimeError('no ACLs defined in available ACLs')

        for root in acls.keys():
            if root not in valid_roots:
                raise RuntimeError('invalid ACL root "%s"' % str(root))

    @staticmethod
    def check_acl_validation_methods(acls: dict, available_acls: list) -> None:
        validation_methods = ['str_in_csv', 'range', 'samechannel', 'disallow']
        validations = acls.get('validation')

        for validation in validations:
            if validation not in available_acls:
                raise RuntimeError('validation for unknown ACL "%s"' % validation)
            if 'type' not in validations[validation]:
                raise RuntimeError('no type in validation for ACL "%s"' % validation)

            validation_method = validations[validation]['type']
            if 'value' in validations[validation]:
                validation_value = validations[validation]['value']
                if validation_method == 'anything':
                    logger.warn(
                            'validation method set to "anything" but a validation value also '
                            'specified, "%s", ignoring the value' % validation_value)

            if validation_method == 'str_in_csv':
                if 'value' in validations[validation] and len(validations[validation]['value'].strip()) == 0:
                    raise RuntimeError(
                            'validation method set to "%s" but blank validation value specified' % validation_method)

            if validation_method not in validation_methods:
                raise RuntimeError(
                        'unknown validation method "%s", use one of [%s]' %
                        (str(validation_method), ','.join(validation_methods)))

    @staticmethod
    def check_acl_excludes(available_acls: list, excludes: list) -> None:
        for exclude in excludes:
            if exclude not in available_acls:
                raise RuntimeError('can not exclude "%s", not in available acls' % exclude)

    @staticmethod
    def check_acl_keys_in_available(available_acls: list, acl_target: str, keys: set) -> None:
        for acl in keys:
            if acl in available_acls:
                continue
            raise RuntimeError(
                    'specified %s ACL "%s" is not in "available": %s' %
                    (acl_target, acl, ','.join(available_acls)))

    @staticmethod
    def check_acl_rules(acls: dict, all_actions: dict, rules: list) -> None:
        for target, actions in acls.items():
            if target not in all_actions:
                continue

            for acl in actions:
                for rule in actions[acl]:
                    if rule not in rules:
                        raise RuntimeError('unknown rule "%s", need to be one of [%s]' % (str(rule), ','.join(rules)))

    @staticmethod
    def check_acl_actions(check_acls: list, actions: dict, available_acls: list) -> None:
        for acl_target, acls in check_acls:
            if acls is None or len(acls) == 0:
                continue

            for action in acls:
                if action not in actions[acl_target]:
                    raise RuntimeError(
                            'action "%s" is not available for target type "%s"' %
                            (action, acl_target))

                if acls[action] is None:
                    continue

                if not isinstance(acls[action], dict):
                    raise RuntimeError(
                            'acls for actions needs to be a dict but was of type %s' %
                            str(type(acls[action])))

                if 'acls' not in acls[action]:
                    continue

                keys = set(acls[action]['acls'])
                AclConfigValidator.check_acl_keys_in_available(available_acls, acl_target, keys)

                if 'exclude' in acls[action]:
                    excludes = acls[action]['exclude']
                    AclConfigValidator.check_acl_excludes(available_acls, excludes)

    @staticmethod
    def validate_acl_config(acls: dict, check_acls: list) -> None:
        available_acls = acls['available']['acls']
        rules = ['acls', 'exclude']
        actions = {
            'room': ['join', 'create', 'list', 'kick', 'message', 'crossroom', 'ban'],
            'channel': ['create', 'list', 'create', 'message', 'crossroom', 'ban']
        }

        AclConfigValidator.check_acl_roots(acls)
        AclConfigValidator.check_acl_validation_methods(acls, available_acls)
        AclConfigValidator.check_acl_rules(acls, actions, rules)
        AclConfigValidator.check_acl_actions(check_acls, actions, available_acls)
