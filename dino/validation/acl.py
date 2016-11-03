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
from dino.config import ConfigKeys
from dino import environ
from dino import utils

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


class AclValidator(object):
    def is_acl_valid(self, acl_type, acl_value):
        all_acls = environ.env.config.get(ConfigKeys.ACL)
        all_validators = all_acls['validation']

        if acl_type not in all_validators:
            logger.warn('acl type "%s" does not have a validator' % acl_type)
            return False

        validator_func = all_validators[acl_type]['value']
        if not callable(validator_func):
            logger.error('validator for acl type "%s" is not callable' % acl_type)
            return False
        if not isinstance(validator_func, BaseAclValidator):
            logger.error(
                    'validator for acl type "%s" is not of instance BaseAclValidator but "%s"' %
                    (acl_type, str(type(validator_func))))
            return False

        # blank means we're removing it
        if acl_value is None or len(acl_value.strip()) == 0:
            return True

        try:
            validator_func.validate_new_acl(acl_value)
        except ValidationException as e:
            logger.info('new acl value "%s" for type "%s" did not validate: %s' % (acl_value, acl_type, str(e)))
            return False
        return True

    def validate_acl_for_action(self, activity: Activity, target: str, action: str, target_acls: dict) -> (bool, str):
        all_acls = environ.env.config.get(ConfigKeys.ACL)

        if activity.target.object_type is None:
            return False, 'target.objectType must not be none'

        # one-to-one is sending message that users private room, so target is room, but object_type would not be
        if target == 'room' and activity.target.object_type != 'room':
            return True, None

        user_id = activity.actor.id
        channel_id = activity.object.url

        # no acls for this target (room/channel) and action (join/kick/etc)
        if target not in all_acls or action not in all_acls[target] or len(all_acls[target][action]) == 0:
            return False, 'no acl set that allows action "%s" for target type "%s"' % (action, target)

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

        origin_channel_id = activity.provider.url
        if origin_channel_id is None or len(origin_channel_id.strip()) == 0:
            return False, 'no origin channel uuid in actor.url'

        target_channel_id = activity.object.url
        if target_channel_id is None or len(target_channel_id.strip()) == 0:
            return False, 'no target channel uuid in object.url'

        if origin_channel_id == target_channel_id:
            return True, None
        return False, 'channels are not the same'


class AclSameRoomValidator(BaseAclValidator):
    def __init__(self):
        pass

    def validate_new_acl(self, values):
        pass

    def __call__(self, *args, **kwargs):
        activity = args[0]
        # env = args[1]
        # acl_type = args[2]
        # acl_values = args[3]
        origin_room_id = activity.actor.url
        if origin_room_id is None or len(origin_room_id.strip()) == 0:
            return False, 'no origin room uuid in actor.url'

        target_room_id = activity.object.url
        if target_room_id is None or len(target_room_id.strip()) == 0:
            return False, 'no target room uuid in object.url'

        if not utils.is_user_in_room(activity.actor.id, target_room_id):
            return False, 'user is not in room, not allowed'

        if origin_room_id == target_room_id:
            return True, None
        return False, 'rooms are not the same'


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
            return False, 'value too low'
        if range_max is not None and range_max < value:
            return False, 'value too high'
        return True, None


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
        validation_methods = ['str_in_csv', 'range', 'samechannel', 'sameroom', 'disallow']
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
            'room': ['join', 'setacl', 'history', 'create', 'list', 'kick', 'message', 'crossroom', 'ban'],
            'channel': ['create', 'setacl', 'list', 'create', 'message', 'crossroom', 'ban']
        }

        AclConfigValidator.check_acl_roots(acls)
        AclConfigValidator.check_acl_validation_methods(acls, available_acls)
        AclConfigValidator.check_acl_rules(acls, actions, rules)
        AclConfigValidator.check_acl_actions(check_acls, actions, available_acls)
