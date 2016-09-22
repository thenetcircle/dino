from flask import session
from activitystreams import Activity
import re

from gridchat.env import env, ConfigKeys


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

    USER_KEYS = {
        'gender':
            lambda v: Validator._chars_in_list(v, ['m', 'f', 'ts']),

        'membership':
            lambda v: Validator._chars_in_list(v, ['0', '1', '2', '3', '4']),

        'age':
            lambda v: Validator._age(v),

        # 2 character country codes, no spaces
        'country':
            lambda v: Validator._match(v, '^([A-Za-z]{2},)*([A-Za-z]{2})+$'),

        # city names can have spaces and dashes in them
        'city':
            lambda v: Validator._match(v, '^([\w -]+,)*([\w -]+)+$'),

        'image':
            lambda v: Validator._true_false_all(v),

        'user_id':
            lambda v: Validator.is_digit(v),

        'user_name':
            lambda v: Validator._is_string(v) and len(v) > 0,

        'token':
            lambda v: Validator._is_string(v) and len(v) > 0,

        'has_webcam':
            lambda v: Validator._true_false_all(v),

        'fake_checked':
            lambda v: Validator._true_false_all(v),
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
    for key in Validator.USER_KEYS.keys():
        if key not in session:
            return False, '"%s" is a required parameter' % key
        val = session[key]
        if val is None or val == '':
            return False, '"%s" is a required parameter' % key
    return True, None


def validate_request(activity: Activity) -> (bool, str):
    if not hasattr(activity, 'actor'):
        return False, 'no actor on activity'

    if not hasattr(activity.actor, 'id'):
        return False, 'no ID on actor'

    if activity.actor.id != env.config.get(ConfigKeys.SESSION).get('user_id', ''):
        return False, "user_id in session (%s) doesn't match user_id in request (%s)" % \
               (activity.actor.id, session['user_id'])

    return True, None


def is_acl_valid(acl_type, acl_value):
    validator = Validator.USER_KEYS.get(acl_type, None)
    if validator is None:
        return False
    if not callable(validator):
        return False
    return validator(acl_value)
