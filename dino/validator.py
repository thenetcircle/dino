from activitystreams import Activity
import re

from dino import environ
from dino import utils
from dino.config import SessionKeys


class Validator:
    @staticmethod
    def is_digit(val: str):
        if not Validator._is_string(val) or len(val) == 0:
            return False
        if val[0] in ('-', '+'):
            return val[1:].isdigit()
        return val.isdigit()

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

        if start is not None and (not Validator.is_digit(start) or int(start) < 0):
            return False
        if end is not None and (not Validator.is_digit(end) or int(end) < 0):
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

        if expected != '' and not Validator._age(expected) or not Validator.is_digit(actual):
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
    def _is_string(val: str):
        return val is not None and isinstance(val, str)

    @staticmethod
    def _chars_in_list(val: str, char_list: list):
        if not Validator._is_string(val):
            return False

        if len(val) == 0:
            return False

        return len([x for x in val.split(',') if x in char_list]) == len(val.split(','))

    @staticmethod
    def _match(val: str, regex: str):
        return Validator._is_string(val) and re.match(regex, val) is not None

    @staticmethod
    def generic_validator(expected, actual):
        return expected is None or actual in expected.split(',')

    ACL_MATCHERS = {
        SessionKeys.age.value:
            lambda expected, actual: expected is None or Validator._age_range_validate(expected, actual),

        SessionKeys.gender.value:
            lambda expected, actual: Validator.generic_validator(expected, actual),

        SessionKeys.membership.value:
            lambda expected, actual: Validator.generic_validator(expected, actual),

        SessionKeys.group.value:
            lambda expected, actual: Validator.generic_validator(expected, actual),

        SessionKeys.country.value:
            lambda expected, actual: Validator.generic_validator(expected, actual),

        SessionKeys.city.value:
            lambda expected, actual: Validator.generic_validator(expected, actual),

        SessionKeys.image.value:
            lambda expected, actual: Validator.generic_validator(expected, actual),

        SessionKeys.has_webcam.value:
            lambda expected, actual: Validator.generic_validator(expected, actual),

        SessionKeys.fake_checked.value:
            lambda expected, actual: Validator.generic_validator(expected, actual)
    }

    ACL_VALIDATORS = {
        SessionKeys.gender.value:
            lambda v: v is None or Validator._chars_in_list(v, ['m', 'f', 'ts']),

        SessionKeys.membership.value:
            lambda v: v is None or Validator._chars_in_list(v, ['0', '1', '2', '3', '4']),

        SessionKeys.age.value:
            lambda v: v is None or Validator._age(v),

        # 2 character country codes, no spaces
        SessionKeys.country.value:
            lambda v: v is None or Validator._match(v, '^([A-Za-z]{2},)*([A-Za-z]{2})+$'),

        # city names can have spaces and dashes in them
        SessionKeys.city.value:
            lambda v: v is None or Validator._match(v, '^([\w -]+,)*([\w -]+)+$'),

        SessionKeys.image.value:
            lambda v: v is None or Validator._true_false_all(v),

        SessionKeys.group.value:
            lambda v: v is None or Validator._is_string(v) and len(v) > 0,

        'user_id':
            lambda v: Validator.is_digit(v),

        'user_name':
            lambda v: Validator._is_string(v) and len(v) > 0,

        'token':
            lambda v: Validator._is_string(v) and len(v) > 0,

        SessionKeys.has_webcam.value:
            lambda v: v is None or Validator._true_false_all(v),

        SessionKeys.fake_checked.value:
            lambda v: v is None or Validator._true_false_all(v),
    }


def validate_login(user_id: str, token: str) -> (bool, str):
    """
    checks whether required data was received and that it validates with community (not tampered with)

    :param user_id: the id of the user
    :param token: the token of the user to verify
    :return: tuple(Boolean, String): (is_valid, error_message)
    """
    is_valid, error_msg, session = environ.env.auth.authenticate_and_populate_session(user_id, token)
    if not is_valid:
        return False, error_msg, None

    is_valid, error_msg = validate_session(session)
    return is_valid, error_msg, session


def validate_user_data_with_community() -> (bool, str):
    """
    :return: tuple(Boolean, String): (is_valid, error_message)
    """
    # todo: ask remote community if the user data is valid (could have been manually changed in js)
    # environ.env.auth_handler.auth(environ.env.session)
    return True, None


def validate_session(session: dict) -> (bool, str):
    """
    validate that all required parameters were send from the client side

    :param session: the session dict to validate
    :return: tuple(Boolean, String): (is_valid, error_message)
    """
    for session_key in SessionKeys:
        key = session_key.value

        if key not in SessionKeys.requires_session_keys.value:
            continue

        if key not in session:
            return False, '"%s" is a required parameter' % key

        val = session[key]
        if val is None or val == '':
            return False, '"%s" is a required parameter' % key
    return True, None


def validate_request(activity: Activity) -> (bool, str):
    if not hasattr(activity.actor, 'id') or activity.actor.id is None:
        return False, 'no ID on actor'

    session_user_id = environ.env.session.get('user_id', 'NOT_FOUND_IN_SESSION')
    if activity.actor.id != session_user_id:
        error_msg = "user_id in session '%s' doesn't match user_id in request '%s'"
        return False, error_msg % (session_user_id, activity.actor.id)

    return True, None


def validate_acl(activity: Activity) -> (bool, str):
    room_id = activity.target.id
    room_name = environ.env.storage.get_room_name(room_id)
    user_id = environ.env.session.get('user_id', 'NOT_FOUND_IN_SESSION')
    user_name = environ.env.session.get('user_name', 'NOT_FOUND_IN_SESSION')

    # owners can always join
    # todo: maybe not if banned? or remove owner status if banned?
    # todo: let admins always be able to join any room
    if utils.is_owner(room_id, user_id):
        _msg = 'user %s (%s) is an owner of room %s (%s), skipping ACL validation'
        environ.env.logger.debug(_msg % (user_id, user_name, room_id, room_name))
        return True, None

    all_acls = environ.env.storage.get_acls(room_id)
    if len(all_acls) == 0:
        return True, None

    for acl_key, acl_val in all_acls.items():
        if acl_key not in environ.env.session:
            error_msg = 'Key "%s" not in session for user "%s" (%s), cannot let join "%s" (%s)'
            error_msg %= (acl_key, user_id, user_name, room_id, room_name)
            environ.env.logger.error(error_msg)
            return False, error_msg

        session_value = environ.env.session.get(acl_key, None)
        if session_value is None:
            error_msg = 'Value for key "%s" not in session, cannot let "%s" (%s) join "%s" (%s)'
            error_msg %= (acl_key, user_id, user_name, room_id, room_name)
            environ.env.logger.error(error_msg)
            return False, error_msg

        if acl_key not in Validator.ACL_MATCHERS:
            error_msg = 'No validator for ACL type "%s", cannot let "%s" (%s) join "%s" (%s)'
            error_msg %= (acl_key, user_id, user_name, room_id, room_name)
            environ.env.logger.error(error_msg)
            return False, error_msg

        validator = Validator.ACL_MATCHERS[acl_key]
        if not callable(validator):
            error_msg = 'Validator for ACL type "%s" is not callable, cannot let "%s" (%s) join "%s" (%s)'
            error_msg %= (acl_key, user_id, user_name, room_id, room_name)
            environ.env.logger.error(error_msg)
            return False, error_msg

        if not validator(acl_val, session_value):
            error_msg = 'Value "%s" did not validate for ACL "%s" (value "%s"), cannot let "%s" (%s) join "%s" (%s)'
            error_msg %= (session_value, acl_key, acl_val, user_id, user_name, room_id, room_name)
            environ.env.logger.info(error_msg)
            return False, error_msg

    return True, None


def is_acl_valid(acl_type, acl_value):
    validator = Validator.ACL_VALIDATORS.get(acl_type, None)
    if validator is None:
        return False
    if not callable(validator):
        return False
    return validator(acl_value)
