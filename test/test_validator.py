import unittest

from gridchat.validator import *


class ValidatorAgeTest(unittest.TestCase):
    def test_valid_start_and_end(self):
        self.assertTrue(Validator._age('18:49'))

    def test_valid_start_only(self):
        self.assertTrue(Validator._age('18:'))

    def test_valid_end_only(self):
        self.assertTrue(Validator._age(':49'))

    def test_no_start_or_end_is_not_valid(self):
        self.assertFalse(Validator._age(':'))

    def test_empty_is_not_valid(self):
        self.assertFalse(Validator._age(''))

    def test_none_is_not_valid(self):
        self.assertFalse(Validator._age(None))

    def test_start_not_numeric(self):
        self.assertFalse(Validator._age('abc:34'))

    def test_end_not_numeric(self):
        self.assertFalse(Validator._age('18:def'))

    def test_start_and_end_not_numeric(self):
        self.assertFalse(Validator._age('abc:def'))

    def test_end_less_than_start_not_valid(self):
        self.assertFalse(Validator._age('34:18'))

    def test_start_less_than_end_is_valid(self):
        self.assertTrue(Validator._age('18:34'))

    def test_start_has_to_be_positive(self):
        self.assertFalse(Validator._age('-18:34'))

    def test_end_has_to_be_positive(self):
        self.assertFalse(Validator._age(':-4'))

    def test_start_and_end_has_to_be_positive(self):
        self.assertFalse(Validator._age('-8:-4'))

    def test_start_and_end_equal_is_valid(self):
        self.assertTrue(Validator._age('20:20'))

    def test_needs_to_be_numeric_not_spaces(self):
        self.assertFalse(Validator._age('  :  '))


class ValidatorGenderTest(unittest.TestCase):
    def test_valid_gender_m(self):
        self.assertTrue(Validator.USER_KEYS['gender']('m'))

    def test_valid_gender_f(self):
        self.assertTrue(Validator.USER_KEYS['gender']('f'))

    def test_valid_gender_ts(self):
        self.assertTrue(Validator.USER_KEYS['gender']('ts'))

    def test_invalid_gender_x(self):
        self.assertFalse(Validator.USER_KEYS['gender']('x'))

    def test_valid_genders_m_f(self):
        self.assertTrue(Validator.USER_KEYS['gender']('m,f'))

    def test_valid_genders_m_f_ts(self):
        self.assertTrue(Validator.USER_KEYS['gender']('m,f,ts'))

    def test_one_invalid_gender_x(self):
        self.assertFalse(Validator.USER_KEYS['gender']('m,x,f'))

    def test_empty_not_valid(self):
        self.assertFalse(Validator.USER_KEYS['gender'](''))

    def test_only_comma_not_valid(self):
        self.assertFalse(Validator.USER_KEYS['gender'](','))

    def test_none_not_valid(self):
        self.assertFalse(Validator.USER_KEYS['gender'](None))


class ValidatorMembershipTest(unittest.TestCase):
    def test_valid_membership_0(self):
        self.assertTrue(Validator.USER_KEYS['membership']('0'))

    def test_valid_membership_1(self):
        self.assertTrue(Validator.USER_KEYS['membership']('1'))

    def test_valid_membership_2(self):
        self.assertTrue(Validator.USER_KEYS['membership']('2'))

    def test_valid_membership_3(self):
        self.assertTrue(Validator.USER_KEYS['membership']('3'))

    def test_valid_membership_4(self):
        self.assertTrue(Validator.USER_KEYS['membership']('4'))

    def test_valid_memberships_0_1_2_3_4(self):
        self.assertTrue(Validator.USER_KEYS['membership']('0,1,2,3,4'))

    def test_ending_in_comma_not_valid(self):
        self.assertFalse(Validator.USER_KEYS['membership']('0,1,2,3,'))

    def test_starting_with_comma_not_valid(self):
        self.assertFalse(Validator.USER_KEYS['membership'](',1,2,3'))

    def test_starting_and_ending_in_comma_not_valid(self):
        self.assertFalse(Validator.USER_KEYS['membership'](',0,1,2,3,'))

    def test_valid_memberships_1_4(self):
        self.assertTrue(Validator.USER_KEYS['membership']('1,4'))

    def test_invalid_membership_x(self):
        self.assertFalse(Validator.USER_KEYS['membership']('x'))

    def test_invalid_membership_9(self):
        self.assertFalse(Validator.USER_KEYS['membership']('9'))

    def test_one_invalid_membership_x(self):
        self.assertFalse(Validator.USER_KEYS['membership']('0,x,4'))

    def test_one_invalid_membership_9(self):
        self.assertFalse(Validator.USER_KEYS['membership']('0,9,4'))

    def test_empty_not_valid(self):
        self.assertFalse(Validator.USER_KEYS['membership'](''))

    def test_only_comma_not_valid(self):
        self.assertFalse(Validator.USER_KEYS['membership'](','))

    def test_none_not_valid(self):
        self.assertFalse(Validator.USER_KEYS['membership'](None))


class ValidatorCountryTest(unittest.TestCase):
    def test_valid_county_de(self):
        self.assertTrue(Validator.USER_KEYS['country']('de'))

    def test_valid_county_cn(self):
        self.assertTrue(Validator.USER_KEYS['country']('cn'))

    def test_valid_counties_de_cn(self):
        self.assertTrue(Validator.USER_KEYS['country']('de,cn'))

    def test_valid_counties_de_cn_with_unknown_xx(self):
        self.assertTrue(Validator.USER_KEYS['country']('de,xx,cn'))

    def test_number_not_ok(self):
        self.assertFalse(Validator.USER_KEYS['country']('de,99,cn'))

    def test_space_not_ok(self):
        self.assertFalse(Validator.USER_KEYS['country']('d ,99,cn'))

    def test_only_two_char_cc_is_valid(self):
        self.assertFalse(Validator.USER_KEYS['country']('de,xx,cnn'))

    def test_ending_in_comma_not_valid(self):
        self.assertFalse(Validator.USER_KEYS['country']('de,cn,'))

    def test_starting_with_comma_not_valid(self):
        self.assertFalse(Validator.USER_KEYS['country'](',de,cn'))

    def test_starting_with_comma_one_cc_not_valid(self):
        self.assertFalse(Validator.USER_KEYS['country'](',de'))

    def test_ending_with_comma_one_cc_not_valid(self):
        self.assertFalse(Validator.USER_KEYS['country']('de,'))

    def test_starting_and_ending_with_comma_one_cc_not_valid(self):
        self.assertFalse(Validator.USER_KEYS['country'](',de,'))

    def test_empty_not_valid(self):
        self.assertFalse(Validator.USER_KEYS['country'](''))

    def test_only_comma_not_valid(self):
        self.assertFalse(Validator.USER_KEYS['country'](','))

    def test_none_not_valid(self):
        self.assertFalse(Validator.USER_KEYS['country'](None))


class ValidatorCityTest(unittest.TestCase):
    def test_valid_city_berlin(self):
        self.assertTrue(Validator.USER_KEYS['city']('Berlin'))

    def test_valid_city_berlin_shanghai(self):
        self.assertTrue(Validator.USER_KEYS['city']('Berlin,Shanghai'))

    def test_valid_city_rio(self):
        self.assertTrue(Validator.USER_KEYS['city']('Rio de Janeiro'))

    def test_valid_city_shanghai_rio_berlin(self):
        self.assertTrue(Validator.USER_KEYS['city']('Shanghai,Rio de Janeiro,Berlin'))

    def test_end_in_comma_not_valid(self):
        self.assertFalse(Validator.USER_KEYS['city']('Shanghai,Rio de Janeiro,Berlin,'))

    def test_starts_with_comma_not_valid(self):
        self.assertFalse(Validator.USER_KEYS['city'](',Shanghai,Rio de Janeiro,Berlin'))

    def test_starts_and_ends_in_comma_not_valid(self):
        self.assertFalse(Validator.USER_KEYS['city'](',Shanghai,Rio de Janeiro,Berlin,'))

    def test_empty_not_valid(self):
        self.assertFalse(Validator.USER_KEYS['city'](''))

    def test_only_comma_not_valid(self):
        self.assertFalse(Validator.USER_KEYS['city'](','))

    def test_none_not_valid(self):
        self.assertFalse(Validator.USER_KEYS['city'](None))
