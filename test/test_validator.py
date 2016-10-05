from dino.validator import Validator
from dino.validator import validate_request
from dino.validator import is_acl_valid
from dino.env import SessionKeys

from activitystreams import parse as as_parser
from uuid import uuid4 as uuid

from test.utils import BaseTest


class ValidatorIsAclValidTest(BaseTest):
    def test_is_valid(self):
        self.assertTrue(is_acl_valid(SessionKeys.gender.value, 'f'))

    def test_missing_is_invalid(self):
        self.assertFalse(is_acl_valid('not-found', 'f'))

    def test_not_callable_is_invalid(self):
        invalid_key = 'not-found'
        Validator.ACL_VALIDATORS[invalid_key] = 'not-callable'
        self.assertFalse(is_acl_valid(invalid_key, 'f'))
        del Validator.ACL_VALIDATORS[invalid_key]


class ValidatorRequestTest(BaseTest):
    def test_no_actor(self):
        response = validate_request(as_parser({
            'verb': 'test',
            'target': {
                'id': 'foo',
                'content': 'bar'
            }
        }))
        self.assertEqual(False, response[0])

    def test_with_actor(self):
        response = validate_request(as_parser({
            'actor': {
                'id': ValidatorRequestTest.USER_ID
            },
            'verb': 'test',
            'target': {
                'id': 'foo',
                'content': 'bar'
            }
        }))
        self.assertEqual(True, response[0])

    def test_with_wrong_actor_id(self):
        response = validate_request(as_parser({
            'actor': {
                'id': str(uuid())
            },
            'verb': 'test',
            'target': {
                'id': 'foo',
                'content': 'bar'
            }
        }))
        self.assertEqual(False, response[0])


class ValidatorAgeMatcherTest(BaseTest):
    def test_valid_no_end(self):
        self.assertTrue(Validator.ACL_MATCHERS[SessionKeys.age.value]('18:', '20'))

    def test_valid_no_start(self):
        self.assertTrue(Validator.ACL_MATCHERS[SessionKeys.age.value](':25', '20'))

    def test_valid_no_start_or_end(self):
        self.assertTrue(Validator.ACL_MATCHERS[SessionKeys.age.value]('', '20'))

    def test_valid_not_a_digit(self):
        self.assertFalse(Validator.ACL_MATCHERS[SessionKeys.age.value]('18:30', '?'))


class ValidatorAgeTest(BaseTest):
    def test_valid_start_and_end(self):
        self.assertTrue(Validator.ACL_VALIDATORS['age']('18:49'))

    def test_valid_start_after_end(self):
        self.assertFalse(Validator.ACL_VALIDATORS['age']('49:18'))

    def test_age_is_not_a_range(self):
        self.assertFalse(Validator.ACL_VALIDATORS['age']('49'))

    def test_valid_start_only(self):
        self.assertTrue(Validator.ACL_VALIDATORS['age']('18:'))

    def test_valid_end_only(self):
        self.assertTrue(Validator.ACL_VALIDATORS['age'](':49'))

    def test_no_start_or_end_is_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['age'](':'))

    def test_empty_is_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['age'](''))

    def test_none_is_valid(self):
        self.assertTrue(Validator.ACL_VALIDATORS['age'](None))

    def test_start_not_numeric(self):
        self.assertFalse(Validator.ACL_VALIDATORS['age']('abc:34'))

    def test_end_not_numeric(self):
        self.assertFalse(Validator.ACL_VALIDATORS['age']('18:def'))

    def test_start_and_end_not_numeric(self):
        self.assertFalse(Validator.ACL_VALIDATORS['age']('abc:def'))

    def test_end_less_than_start_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['age']('34:18'))

    def test_start_less_than_end_is_valid(self):
        self.assertTrue(Validator.ACL_VALIDATORS['age']('18:34'))

    def test_start_has_to_be_positive(self):
        self.assertFalse(Validator.ACL_VALIDATORS['age']('-18:34'))

    def test_end_has_to_be_positive(self):
        self.assertFalse(Validator.ACL_VALIDATORS['age'](':-4'))

    def test_start_and_end_has_to_be_positive(self):
        self.assertFalse(Validator.ACL_VALIDATORS['age']('-8:-4'))

    def test_start_and_end_equal_is_valid(self):
        self.assertTrue(Validator.ACL_VALIDATORS['age']('20:20'))

    def test_needs_to_be_numeric_not_spaces(self):
        self.assertFalse(Validator.ACL_VALIDATORS['age']('  :  '))


class ValidatorGenderTest(BaseTest):
    def test_valid_gender_m(self):
        self.assertTrue(Validator.ACL_VALIDATORS['gender']('m'))

    def test_valid_gender_f(self):
        self.assertTrue(Validator.ACL_VALIDATORS['gender']('f'))

    def test_valid_gender_ts(self):
        self.assertTrue(Validator.ACL_VALIDATORS['gender']('ts'))

    def test_invalid_gender_x(self):
        self.assertFalse(Validator.ACL_VALIDATORS['gender']('x'))

    def test_valid_genders_m_f(self):
        self.assertTrue(Validator.ACL_VALIDATORS['gender']('m,f'))

    def test_valid_genders_m_f_ts(self):
        self.assertTrue(Validator.ACL_VALIDATORS['gender']('m,f,ts'))

    def test_one_invalid_gender_x(self):
        self.assertFalse(Validator.ACL_VALIDATORS['gender']('m,x,f'))

    def test_empty_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['gender'](''))

    def test_only_comma_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['gender'](','))

    def test_none_is_valid(self):
        self.assertTrue(Validator.ACL_VALIDATORS['gender'](None))


class ValidatorMembershipTest(BaseTest):
    def test_valid_membership_0(self):
        self.assertTrue(Validator.ACL_VALIDATORS['membership']('0'))

    def test_valid_membership_1(self):
        self.assertTrue(Validator.ACL_VALIDATORS['membership']('1'))

    def test_valid_membership_2(self):
        self.assertTrue(Validator.ACL_VALIDATORS['membership']('2'))

    def test_valid_membership_3(self):
        self.assertTrue(Validator.ACL_VALIDATORS['membership']('3'))

    def test_valid_membership_4(self):
        self.assertTrue(Validator.ACL_VALIDATORS['membership']('4'))

    def test_valid_memberships_0_1_2_3_4(self):
        self.assertTrue(Validator.ACL_VALIDATORS['membership']('0,1,2,3,4'))

    def test_ending_in_comma_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['membership']('0,1,2,3,'))

    def test_starting_with_comma_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['membership'](',1,2,3'))

    def test_starting_and_ending_in_comma_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['membership'](',0,1,2,3,'))

    def test_valid_memberships_1_4(self):
        self.assertTrue(Validator.ACL_VALIDATORS['membership']('1,4'))

    def test_invalid_membership_x(self):
        self.assertFalse(Validator.ACL_VALIDATORS['membership']('x'))

    def test_invalid_membership_9(self):
        self.assertFalse(Validator.ACL_VALIDATORS['membership']('9'))

    def test_one_invalid_membership_x(self):
        self.assertFalse(Validator.ACL_VALIDATORS['membership']('0,x,4'))

    def test_one_invalid_membership_9(self):
        self.assertFalse(Validator.ACL_VALIDATORS['membership']('0,9,4'))

    def test_empty_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['membership'](''))

    def test_only_comma_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['membership'](','))

    def test_none_is_valid(self):
        self.assertTrue(Validator.ACL_VALIDATORS['membership'](None))


class ValidatorCountryTest(BaseTest):
    def test_valid_county_de(self):
        self.assertTrue(Validator.ACL_VALIDATORS['country']('de'))

    def test_valid_county_cn(self):
        self.assertTrue(Validator.ACL_VALIDATORS['country']('cn'))

    def test_valid_counties_de_cn(self):
        self.assertTrue(Validator.ACL_VALIDATORS['country']('de,cn'))

    def test_valid_counties_de_cn_with_unknown_xx(self):
        self.assertTrue(Validator.ACL_VALIDATORS['country']('de,xx,cn'))

    def test_number_not_ok(self):
        self.assertFalse(Validator.ACL_VALIDATORS['country']('de,99,cn'))

    def test_space_not_ok(self):
        self.assertFalse(Validator.ACL_VALIDATORS['country']('d ,99,cn'))

    def test_only_two_char_cc_is_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['country']('de,xx,cnn'))

    def test_ending_in_comma_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['country']('de,cn,'))

    def test_starting_with_comma_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['country'](',de,cn'))

    def test_starting_with_comma_one_cc_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['country'](',de'))

    def test_ending_with_comma_one_cc_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['country']('de,'))

    def test_starting_and_ending_with_comma_one_cc_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['country'](',de,'))

    def test_empty_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['country'](''))

    def test_only_comma_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['country'](','))

    def test_none_is_valid(self):
        self.assertTrue(Validator.ACL_VALIDATORS['country'](None))


class ValidatorCityTest(BaseTest):
    def test_valid_city_berlin(self):
        self.assertTrue(Validator.ACL_VALIDATORS['city']('Berlin'))

    def test_valid_city_berlin_shanghai(self):
        self.assertTrue(Validator.ACL_VALIDATORS['city']('Berlin,Shanghai'))

    def test_valid_city_rio(self):
        self.assertTrue(Validator.ACL_VALIDATORS['city']('Rio de Janeiro'))

    def test_valid_city_shanghai_rio_berlin(self):
        self.assertTrue(Validator.ACL_VALIDATORS['city']('Shanghai,Rio de Janeiro,Berlin'))

    def test_end_in_comma_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['city']('Shanghai,Rio de Janeiro,Berlin,'))

    def test_starts_with_comma_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['city'](',Shanghai,Rio de Janeiro,Berlin'))

    def test_starts_and_ends_in_comma_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['city'](',Shanghai,Rio de Janeiro,Berlin,'))

    def test_empty_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['city'](''))

    def test_only_comma_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['city'](','))

    def test_none_is_valid(self):
        self.assertTrue(Validator.ACL_VALIDATORS['city'](None))


class ValidatorImageTest(BaseTest):
    def test_valid_value_y(self):
        self.assertTrue(Validator.ACL_VALIDATORS['image']('y'))

    def test_valid_value_n(self):
        self.assertTrue(Validator.ACL_VALIDATORS['image']('n'))

    def test_valid_value_a(self):
        self.assertTrue(Validator.ACL_VALIDATORS['image']('a'))

    def test_invalid_value_x(self):
        self.assertFalse(Validator.ACL_VALIDATORS['image']('x'))

    def test_two_values_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['image']('y,n'))

    def test_comma_in_start_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['image'](',n'))

    def test_comma_in_end_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['image']('n,'))

    def test_comma_in_end_and_start_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['image'](',n,'))

    def test_yes_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['image']('yes'))

    def test_empty_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['image'](''))

    def test_only_comma_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['image'](','))

    def test_none_is_valid(self):
        self.assertTrue(Validator.ACL_VALIDATORS['image'](None))


class ValidatorWebcamTest(BaseTest):
    def test_valid_value_y(self):
        self.assertTrue(Validator.ACL_VALIDATORS['has_webcam']('y'))

    def test_valid_value_n(self):
        self.assertTrue(Validator.ACL_VALIDATORS['has_webcam']('n'))

    def test_valid_value_a(self):
        self.assertTrue(Validator.ACL_VALIDATORS['has_webcam']('a'))

    def test_invalid_value_x(self):
        self.assertFalse(Validator.ACL_VALIDATORS['has_webcam']('x'))

    def test_two_values_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['has_webcam']('y,n'))

    def test_comma_in_start_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['has_webcam'](',n'))

    def test_comma_in_end_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['has_webcam']('n,'))

    def test_comma_in_end_and_start_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['has_webcam'](',n,'))

    def test_yes_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['has_webcam']('yes'))

    def test_empty_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['has_webcam'](''))

    def test_only_comma_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['has_webcam'](','))

    def test_none_is_valid(self):
        self.assertTrue(Validator.ACL_VALIDATORS['has_webcam'](None))


class ValidatorFakeCheckedTest(BaseTest):
    def test_valid_value_y(self):
        self.assertTrue(Validator.ACL_VALIDATORS['fake_checked']('y'))

    def test_valid_value_n(self):
        self.assertTrue(Validator.ACL_VALIDATORS['fake_checked']('n'))

    def test_valid_value_a(self):
        self.assertTrue(Validator.ACL_VALIDATORS['fake_checked']('a'))

    def test_invalid_value_x(self):
        self.assertFalse(Validator.ACL_VALIDATORS['fake_checked']('x'))

    def test_two_values_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['fake_checked']('y,n'))

    def test_comma_in_start_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['fake_checked'](',n'))

    def test_comma_in_end_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['fake_checked']('n,'))

    def test_comma_in_end_and_start_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['fake_checked'](',n,'))

    def test_yes_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['fake_checked']('yes'))

    def test_empty_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['fake_checked'](''))

    def test_only_comma_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['fake_checked'](','))

    def test_none_is_valid(self):
        self.assertTrue(Validator.ACL_VALIDATORS['fake_checked'](None))


class ValidatorUserIdTest(BaseTest):
    def test_invalid_value_y(self):
        self.assertFalse(Validator.ACL_VALIDATORS['user_id']('y'))

    def test_valid_value_1000(self):
        self.assertTrue(Validator.ACL_VALIDATORS['user_id']('1000'))

    def test_space_invalid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['user_id']('10 00'))

    def test_non_numeric_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['user_id']('username'))

    def test_empty_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['user_id'](''))

    def test_none_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['user_id'](None))


class ValidatorUserNameTest(BaseTest):
    def test_valid_username(self):
        self.assertTrue(Validator.ACL_VALIDATORS['user_name']('username'))

    def test_valid_username_numeric(self):
        self.assertTrue(Validator.ACL_VALIDATORS['user_name']('32'))

    def test_valid_username_with_space(self):
        self.assertTrue(Validator.ACL_VALIDATORS['user_name']('user name'))

    def test_valid_username_with_underscore(self):
        self.assertTrue(Validator.ACL_VALIDATORS['user_name']('user_name'))

    def test_empty_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['user_name'](''))

    def test_none_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['user_name'](None))


class ValidatorTokenTest(BaseTest):
    def test_valid_username(self):
        self.assertTrue(Validator.ACL_VALIDATORS['token']('10192387'))

    def test_valid_username_numeric(self):
        self.assertTrue(Validator.ACL_VALIDATORS['token']('32'))

    def test_valid_username_with_space(self):
        self.assertTrue(Validator.ACL_VALIDATORS['token']('something else'))

    def test_valid_username_with_underscore(self):
        self.assertTrue(Validator.ACL_VALIDATORS['token']('to_ken'))

    def test_empty_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['token'](''))

    def test_none_is_not_valid(self):
        self.assertFalse(Validator.ACL_VALIDATORS['token'](None))
