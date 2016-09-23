from activitystreams import Activity
import re

from gridchat import rkeys
from gridchat.env import env, ConfigKeys
from gridchat import utils


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

        if not Validator._age(expected) or not Validator.is_digit(actual):
            return False

        expected_start, expected_end = _split_age(actual.strip())

        if expected_start is None and expected_end is None:
            return False

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
        return Validator._is_string(val) and len(val) > 0 and \
               len([x for x in val.split(',') if x in char_list]) == len(val.split(','))

    @staticmethod
    def _match(val: str, regex: str):
        return Validator._is_string(val) and re.match(regex, val) is not None

    @staticmethod
    def generic_validator(expected, actual):
        return expected is None or actual in expected.split(',')

    ACL_VALIDATORS = {
        'age':
            lambda expected, actual: expected is None or Validator._age_range_validate(expected, actual),

        'gender': generic_validator,
        'membership': generic_validator,
        'country': generic_validator,
        'city': generic_validator,
        'image': generic_validator,
        'has_webcam': generic_validator,
        'fake_checked': generic_validator
    }

    USER_KEYS = {
        'gender':
            lambda v: v is None or Validator._chars_in_list(v, ['m', 'f', 'ts']),

        'membership':
            lambda v: v is None or Validator._chars_in_list(v, ['0', '1', '2', '3', '4']),

        'age':
            lambda v: v is None or Validator._age(v),

        # 2 character country codes, no spaces
        'country':
            lambda v: v is None or Validator._match(v, '^([A-Za-z]{2},)*([A-Za-z]{2})+$'),

        # city names can have spaces and dashes in them
        'city':
            lambda v: v is None or Validator._match(v, '^([\w -]+,)*([\w -]+)+$'),

        'image':
            lambda v: v is None or Validator._true_false_all(v),

        'user_id':
            lambda v: Validator.is_digit(v),

        'user_name':
            lambda v: Validator._is_string(v) and len(v) > 0,

        'token':
            lambda v: Validator._is_string(v) and len(v) > 0,

        'has_webcam':
            lambda v: v is None or Validator._true_false_all(v),

        'fake_checked':
            lambda v: v is None or Validator._true_false_all(v),
    }


def validate() -> (bool, str):
    """
    checks whether required data was received and that it validates with community (not tampered with)

    :return: tuple(Boolean, String): (is_valid, error_message)
    """
    is_valid, error_msg = validate_session()
    if not is_valid:
        return False, error_msg

    return validate_user_data_with_community()


def validate_user_data_with_community() -> (bool, str):
    """
    todo: ask remote community if the user data is valid (could have been manually changed in js)

    :return: tuple(Boolean, String): (is_valid, error_message)
    """
    return True, None


def validate_session() -> (bool, str):
    """
    validate that all required parameters were send from the client side

    :return: tuple(Boolean, String): (is_valid, error_message)
    """
    session = env.session()
    for key in Validator.USER_KEYS.keys():
        if key not in session:
            return False, '"%s" is a required parameter' % key
        val = session[key]
        if val is None or val == '':
            return False, '"%s" is a required parameter' % key
    return True, None


def validate_request(activity: Activity) -> (bool, str):
    session = env.session()

    if not hasattr(activity, 'actor'):
        return False, 'no actor on activity'

    if not hasattr(activity.actor, 'id'):
        return False, 'no ID on actor'

    if activity.actor.id != session.get('user_id', 'NOT_FOUND_IN_SESSION'):
        return False, "user_id in session (%s) doesn't match user_id in request (%s)" % \
               (activity.actor.id, session.get('user_id', 'NOT_FOUND_IN_SESSION'))

    return True, None


def validate_acl(activity: Activity) -> (bool, str):
    session = env.session()
    redis = env.redis()
    logger = env.logger()

    room_id = activity.target.id
    room_name = utils.get_room_name(redis, room_id)
    user_id = session.get('user_id', 'NOT_FOUND_IN_SESSION')
    user_name = session.get('user_name', 'NOT_FOUND_IN_SESSION')

    encoded_acls = redis.hgetall(rkeys.room_acl(room_id))
    if len(encoded_acls) == 0:
        return True, None

    for acl_key, acl_val in encoded_acls.items():
        acl_key = str(acl_key, 'utf-8')
        acl_val = str(acl_val, 'utf-8')

        if acl_key not in session:
            error_msg = 'Key "%s" not in session for user "%s" (%s), cannot let join "%s" (%s)' % \
                   (acl_key, user_id, user_name, room_id, utils.get_room_name(redis, room_id))
            logger.error(error_msg)
            return False, error_msg

        session_value = session.get(acl_key, None)
        if session_value is None:
            error_msg = 'Value for key "%s" not in session, cannot let "%s" (%s) join "%s" (%s)' % \
                   (acl_key, user_id, user_name, room_id, room_name)
            logger.error(error_msg)
            return False, error_msg

        if acl_key not in Validator.ACL_VALIDATORS:
            error_msg = 'No validator for ACL type "%s", cannot let "%s" (%s) join "%s" (%s)' % \
                        (acl_key, user_id, user_name, room_id, room_name)
            logger.error(error_msg)
            return False, error_msg

        validator = Validator.ACL_VALIDATORS[acl_key]
        if not callable(validator):
            error_msg = 'Validator for ACL type "%s" is not callable, cannot let "%s" (%s) join "%s" (%s)' % \
                        (acl_key, user_id, user_name, room_id, room_name)
            logger.error(error_msg)
            return False, error_msg

        if not validator(acl_val, session_value):
            error_msg = 'Value "%s" did not validate for ACL "%s" (value "%s"), cannot let "%s" (%s) join "%s" (%s)' % \
                   (session_value, acl_key, acl_val, user_id, user_name, room_id, room_name)
            logger.info(error_msg)
            return False, error_msg

    return True, None


def is_acl_valid(acl_type, acl_value):
    validator = Validator.USER_KEYS.get(acl_type, None)
    if validator is None:
        return False
    if not callable(validator):
        return False
    return validator(acl_value)
