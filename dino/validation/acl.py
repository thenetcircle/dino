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
from dino.config import ApiTargets
from dino import environ
from dino import utils

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


class AclValidator(object):
    def is_acl_valid(self, acl_type, acl_value):
        all_acls = environ.env.config.get(ConfigKeys.ACL)
        all_validators = all_acls['validation']

        if acl_type not in all_validators:
            error_msg = 'acl type "%s" does not have a validator' % acl_type
            logger.warn(error_msg)
            return False, error_msg

        validator_func = all_validators[acl_type]['value']
        if not isinstance(validator_func, BaseAclValidator):
            error_msg = 'validator for acl type "%s" is not of instance BaseAclValidator but "%s"' % \
                        (acl_type, str(type(validator_func)))
            logger.error(error_msg)
            return False, error_msg

        # blank means we're removing it
        if acl_value is None or len(acl_value.strip()) == 0:
            return True, None

        try:
            validator_func.validate_new_acl(acl_value)
        except ValidationException as e:
            logger.info('new acl value "%s" for type "%s" did not validate: %s' % (acl_value, acl_type, e.msg))
            return False, e.msg
        return True, None

    def validate_acl_for_action(
            self,
            activity: Activity,
            target: str,
            action: str,
            target_acls: dict,
            target_id: str = None,
            object_type: str = None,
            session_to_use=None,
    ) -> (bool, str):
        # for testing purposes
        if session_to_use is None:
            session_to_use = environ.env.session

        all_acls = environ.env.config.get(ConfigKeys.ACL)

        if not hasattr(activity, 'target') or not hasattr(activity.target, 'object_type'):
            return False, 'target.objectType must not be none'
        if activity.target.object_type is None or len(activity.target.object_type.strip()) == 0:
            return False, 'target.objectType must not be none'

        if target_id is None:
            target_id = activity.target.id
        if object_type is None:
            object_type = activity.target.object_type

        # one-to-one is sending message that users private room, so target is room, but object_type would not be
        if target == ApiTargets.ROOM and object_type != 'room':
            return True, None

        user_id = activity.actor.id
        if target == 'room':
            channel_id = utils.get_channel_for_room(target_id)
        else:
            channel_id = activity.object.url

        if utils.is_admin(channel_id, user_id):
            return True, None
        if utils.is_super_user(user_id):
            return True, None
        if utils.is_global_moderator(user_id):
            return True, None

        # no acls for this target (room/channel) and action (join/kick/etc)
        if target not in all_acls or action not in all_acls[target] or len(all_acls[target][action]) == 0:
            return True, None  # 'no acl set that allows action "%s" for target type "%s"' % (action, target)

        if utils.is_owner_channel(channel_id, user_id):
            return True, None

        if target == 'channel':
            pass
        elif target == 'room':
            if utils.is_owner(target_id, user_id):
                return True, None

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
                is_valid, msg = is_valid_func(activity, environ.env, acl, target_acls[acl], False, session_to_use)
                if not is_valid:
                    return False, 'acl "%s" did not validate for target acl "%s": %s' % (
                        acl, target_acls[acl], msg)

        return True, None


class BaseAclValidator(object):
    def validate_new_acl(self, values):
        raise NotImplementedError('validate_new_acl')


class AclIsAdminValidator(BaseAclValidator):
    def __init__(self):
        pass

    def validate_new_acl(self, values):
        pass

    def __call__(self, *args, **kwargs):
        activity = args[0]
        env = args[1]
        # acl_type = args[2]
        # acl_values = args[3]

        value_is_negated = False
        if len(args) > 4:
            value_is_negated = args[4]

        user_id = activity.actor.id
        channel_id = activity.object.url

        if value_is_negated:
            if not env.db.is_admin(channel_id, user_id):
                return True, None
            return False, 'is admin (ACL negated)'

        if env.db.is_admin(channel_id, user_id):
            return True, None
        return False, 'not admin'


class AclIsRoomOwnerValidator(BaseAclValidator):
    def __init__(self):
        pass

    def validate_new_acl(self, values):
        pass

    def __call__(self, *args, **kwargs):
        activity = args[0]
        env = args[1]
        # acl_type = args[2]
        # acl_values = args[3]

        value_is_negated = False
        if len(args) > 4:
            value_is_negated = args[4]

        user_id = activity.actor.id
        room_id = activity.target.id

        if value_is_negated:
            if not env.db.is_owner(room_id, user_id):
                return True, None
            return False, 'is owner (ACL negated)'

        if env.db.is_owner(room_id, user_id):
            return True, None
        return False, 'not owner'


class AclIsSuperUserValidator(BaseAclValidator):
    def __init__(self):
        pass

    def validate_new_acl(self, values):
        pass

    def __call__(self, *args, **kwargs):
        activity = args[0]
        env = args[1]
        # acl_type = args[2]
        # acl_values = args[3]

        value_is_negated = False
        if len(args) > 4:
            value_is_negated = args[4]

        user_id = activity.actor.id

        if value_is_negated:
            if not env.db.is_super_user(user_id):
                return True, None
            return False, 'is super user (ACL negated)'

        if env.db.is_super_user(user_id):
            return True, None
        return False, 'not super user'


class AclPatternValidator(BaseAclValidator):
    def __init__(self):
        self.acl_type = 'custom'
        pattern = '^[0-9a-z!\|,\(\):=_]*$'

        try:
            import re
            self.pattern = re.compile(pattern)
        except Exception:
            raise ValidationException('invalid pattern: %s' % str(pattern))

    def validate_new_acl(self, values: str):
        if values is None or len(values.strip()) == 0:
            raise ValidationException('blank pattern')

        if self.pattern.match(values) is None:
            raise ValidationException('pattern did not match new value: %s' % values)

        if '(' in values or ')' in values:
            left = len([a for a in values if a == '('])
            right = len([a for a in values if a == ')'])
            if left != right:
                raise ValidationException('parenthesis mismatch in pattern: %s' % values)

            opened, closed = 0, 0
            for c in values:
                if c == '(':
                    opened += 1
                elif c == ')':
                    closed += 1
                if abs(opened - closed) > 1 or closed > opened:
                    raise ValidationException('nest parenthesis not allowed in pattern: %s' % values)

        groups = dict()
        self._split_and_test_clause(groups, values, is_validating_a_user=False)

    def _test_a_clause(self, clause, is_validating_a_user: bool, activity: Activity=None, env=None):
        if '=' not in clause:
            raise ValidationException('no equal sign in clause: %s' % clause)

        if len(clause.split('=')) != 2:
            raise ValidationException('equal sign mismatch in clause: %s' % clause)

        acl_type, acl_value = clause.split('=')
        all_acls = environ.env.config.get(ConfigKeys.ACL)
        all_validators = all_acls['validation']
        if acl_type not in all_validators:
            raise ValidationException(
                    'invalid acl "%s" in clause: %s' % (acl_type, clause))

        if acl_type == 'custom':
            raise ValidationException(
                    'nested custom acls not allowed in clause: %s' % clause)

        value_is_negated = False
        if acl_value[0] == '!':
            acl_value = acl_value[1:]
            value_is_negated = True

        validator_func = all_validators[acl_type]['value']
        if not isinstance(validator_func, BaseAclValidator):
            raise ValidationException(
                    'validator for acl type "%s" is not of instance BaseAclValidator '
                    'but "%s"' % (acl_type, str(type(validator_func))))

        # a user is using the api, so validate his action against set pattern
        if is_validating_a_user:
            if not callable(validator_func):
                raise ValidationException('validator function is not callable')

            is_valid, msg = validator_func(activity, env, acl_type, acl_value, value_is_negated)
            return is_valid, msg
        # now we're validating a new acl rule set in admin interface
        else:
            validator_func.validate_new_acl(acl_value)
            return True, None

    def _split_and_test_clause(self, groups, clause, is_validating_a_user: bool=False, activity: Activity=None, env=None):
        """
        The default value for is_validating_a_user is False, meaning we're validating a new acl rule someone set in the
        admin web interface. In this case the activity and env variables are not used. On the other hand, if
        is_validating_a_user is set to true, it means we're validating the "custom" acl rule for something a user did
        through the API, and in this case the activity and env is needed, since we'll be validating against the user
        info set on the environment for this user, e.g. age, gender or whatever it could be in the current 7
        implementation.

        :param groups: the first time this method is called this dict has to be empty; it is used to store parenthesis
        clauses, so we can split the and/or tokens without affecting the parenthesises; since this method is recursive
        we have to pass this dict throughout the recursion
        :param clause: the value of the "custom" acl, e.g. "gender=m|age=:35,gender=!m"
        :param is_validating_a_user: true means validate a user api action, false means validate a new custom acl rule
        :param activity: the activity the user supplied (if is_validating_a_user is True, None otherwise)
        :param env: the current environ.env (if is_validating_a_user is True, None otherwise)
        :return: nothing
        """
        while '(' in clause:
            pos = len(groups)
            start = clause.index('(')+1
            end = clause.index(')')
            groups[pos] = clause[start:end]
            clause = clause[:start-1] + '@%s@' % pos + clause[end+1:]

        or_clauses = [clause]
        if '|' in clause:
            or_clauses = clause.split('|')

        for or_clause in or_clauses:
            and_clauses = [or_clause]
            if ',' in or_clause:
                and_clauses = or_clause.split(',')

            all_and_ok = True
            for and_clause in and_clauses:
                if '@' in and_clause:
                    if and_clause[0] != '@' or and_clause[-1] != '@' or and_clause.count('@') != 2:
                        raise ValidationException('mismatched at-signs in clause: %s' % and_clause)
                    and_clause = groups[int(and_clause[1:len(and_clause)-1])]

                try:
                    if len([c for c in and_clause if c in '|,']) > 0:
                        self._split_and_test_clause(groups, and_clause, is_validating_a_user, activity, env)
                    else:
                        is_valid, error_msg = self._test_a_clause(and_clause, is_validating_a_user, activity, env)
                        if not is_valid:
                            logger.error('during AND checks: %s' % error_msg)
                            all_and_ok = False
                            break
                except ValidationException as e:
                    logger.error('during AND checks: %s' % e.msg)
                    raise e
            if not all_and_ok:
                continue

            # at least one OR was ok so we can return
            return

        # if more than two we have or clauses, otherwise just one and clause
        if len(or_clauses) > 1:
            raise ValidationException(
                'no OR clause validated true for: %s' % ('|'.join(or_clauses)))
        else:
            raise ValidationException(
                'the AND clause did not validate for: %s' % (or_clauses[0]))

    def __call__(self, *args, **kwargs):
        activity = args[0]

        # contains the session values for age, gender etc.
        env = args[1]

        # this just says 'custom', not used for this validator since 'custom' is not in the session (like e.g. age,
        # gender etc.)
        # acl_type = args[2]

        # this is the custom value set, e.g. "age=23:30|gender=f"
        acl_value = args[3]

        try:
            #  _split_and_test_clause() is called recursively, but we need to retain the extracted parenthesis "groups"
            groups = dict()
            self._split_and_test_clause(groups, acl_value, is_validating_a_user=True, activity=activity, env=env)
        except ValidationException as e:
            logger.error(e.msg)
            return False, e.msg
        return True, None


class AclDisallowValidator(BaseAclValidator):
    def __init__(self):
        pass

    def validate_new_acl(self, values: str):
        pass

    def __call__(self, *args, **kwargs):
        return False, 'not allowed'


class AclSameChannelValidator(BaseAclValidator):
    def __init__(self):
        pass

    def validate_new_acl(self, values: str):
        pass

    def __call__(self, *args, **kwargs):
        activity = args[0]
        # env = args[1]
        # acl_type = args[2]
        # acl_values = args[3]

        value_is_negated = False
        if len(args) > 4:
            value_is_negated = args[4]

        origin_channel_id = activity.provider.url
        if origin_channel_id is None or len(origin_channel_id.strip()) == 0:
            return False, 'no origin channel uuid in actor.url'

        target_channel_id = activity.object.url
        if target_channel_id is None or len(target_channel_id.strip()) == 0:
            return False, 'no target channel uuid in object.url'

        if value_is_negated:
            if origin_channel_id != target_channel_id:
                return True, None
            return False, 'channels are the same (negated ACL)'

        if origin_channel_id == target_channel_id:
            return True, None
        return False, 'channels are not the same'


class AclSameRoomValidator(BaseAclValidator):
    def __init__(self):
        pass

    def validate_new_acl(self, values: str):
        pass

    def __call__(self, *args, **kwargs):
        activity = args[0]
        # env = args[1]
        # acl_type = args[2]
        # acl_values = args[3]

        value_is_negated = False
        if len(args) > 4:
            value_is_negated = args[4]

        origin_room_id = activity.actor.url
        if origin_room_id is None or len(origin_room_id.strip()) == 0:
            return False, 'no origin room uuid in actor.url'

        target_room_id = activity.target.id
        if target_room_id is None or len(target_room_id.strip()) == 0:
            return False, 'no target room uuid in object.url'

        if not utils.is_user_in_room(activity.actor.id, target_room_id):
            return False, 'user is not in room, not allowed'

        if value_is_negated:
            if origin_room_id != target_room_id:
                return True, None
            return False, 'rooms are the same (negated ACL)'

        if origin_room_id == target_room_id:
            return True, None
        return False, 'rooms are not the same'


class AclStrInCsvValidator(BaseAclValidator):
    def __init__(self, csv=None):
        self.valid_csvs = None
        if csv is not None:
            self.valid_csvs = csv.split(',')

    def validate_new_acl(self, values: str):
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

        value_is_negated = False
        if len(args) > 4:
            value_is_negated = args[4]

        session_to_use = env.session
        if len(args) > 5:
            session_to_use = args[5]

        if acl_values.strip() == '':
            return True, None
        acl_values = acl_values.split(',')

        session_value = session_to_use.get(acl_type)
        if session_value is None:
            logger.warning('no session value for acl "%s"' % acl_type)
            return False, 'no session value for acl"%s"' % acl_type

        if value_is_negated:
            if session_value in acl_values:
                return False, 'session value %s is in non-allowed (ACL negated) values [%s]' % \
                       (session_value, ','.join(acl_values))
            return True, None

        if session_value not in acl_values:
            return False, 'session value %s not in allowed values [%s]' % (session_value, ','.join(acl_values))
        return True, None


class AclCsvInCsvValidator(BaseAclValidator):
    def __init__(self, csv=None):
        self.valid_csvs = None
        if csv is not None:
            self.valid_csvs = csv.split(',')

    def validate_new_acl(self, values: str):
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

        value_is_negated = False
        if len(args) > 4:
            value_is_negated = args[4]

        session_to_use = env.session
        if len(args) > 5:
            session_to_use = args[5]

        if acl_values.strip() == '':
            return True, None
        acl_values = acl_values.split(',')

        session_values = session_to_use.get(acl_type)
        if session_values is None:
            logger.warning('no session values for acl "%s"' % acl_type)
            return False, 'no session values for acl"%s"' % acl_type

        if value_is_negated:
            for session_value in session_values.split(","):
                if session_value in acl_values:
                    return False, 'session value %s is in non-allowed (ACL negated) values [%s]' % \
                           (session_value, ','.join(acl_values))
            return True, None

        for session_value in session_values.split(","):
            if session_value.lower() in acl_values:
                return True, None
        return False, 'session values [%s] not in allowed values [%s]' % (session_values, ','.join(acl_values))


class AclRangeValidator(BaseAclValidator):
    def __init__(self):
        pass

    def validate_new_acl(self, values: str):
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

        value_is_negated = False
        if len(args) > 4:
            value_is_negated = args[4]

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

        if value_is_negated:
            if range_min is not None and range_max is not None:
                if range_min <= value <= range_max:
                    return False, 'value withing range (ACL negated)'
            else:
                if range_min is not None and range_min <= value:
                    return False, 'value too high'
                if range_max is not None and range_max >= value:
                    return False, 'value too low'
            return True, None

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
        validation_methods = [
            'str_in_csv', 'range', 'samechannel', 'sameroom', 'disallow',
            'is_admin', 'is_super_user', 'anything', 'custom', 'is_room_owner'
        ]
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
                    logger.warning(
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
            'room': ['join', 'setacl', 'history', 'create', 'list', 'kick', 'message', 'crossroom', 'ban', 'autojoin'],
            'channel': ['create', 'setacl', 'list', 'create', 'message', 'crossroom', 'ban', 'whisper']
        }

        AclConfigValidator.check_acl_roots(acls)
        AclConfigValidator.check_acl_validation_methods(acls, available_acls)
        AclConfigValidator.check_acl_rules(acls, actions, rules)
        AclConfigValidator.check_acl_actions(check_acls, actions, available_acls)
