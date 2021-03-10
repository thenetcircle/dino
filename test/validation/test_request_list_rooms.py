from activitystreams import parse as as_parser

from dino.config import ApiActions
from dino.config import ErrorCodes
from dino.config import SessionKeys
from dino.validation import request
from test.base import BaseTest


class RequestListRoomsTest(BaseTest):
    def test_list_rooms_status_code_true(self):
        self.assert_in_room(False)
        self.create_and_join_room()
        self.assert_in_room(True)

        response_data = request.on_list_rooms(as_parser(self.activity_for_list_rooms()))
        self.assertEqual(True, response_data[0])

    def test_list_rooms_no_actor_id_status_code_false(self):
        self.assert_in_room(False)
        self.create_and_join_room()
        self.assert_in_room(True)

        activity = self.activity_for_list_rooms()
        del activity['actor']['id']
        response_data = request.on_list_rooms(as_parser(activity))
        self.assertEqual(True, response_data[0])

    def test_list_rooms_not_allowed(self):
        self.assert_in_room(False)
        self.set_channel_acl({ApiActions.LIST: {'gender': 'm'}})
        activity = self.activity_for_list_rooms()
        is_valid, code, msg = request.on_list_rooms(as_parser(activity))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.NOT_ALLOWED)

    def test_list_rooms_spoken_country_none(self):
        self._test_spoken_language(False, 'de', None)

    def test_list_rooms_spoken_country_empty(self):
        self._test_spoken_language(False, 'de', '')

    def test_list_rooms_spoken_country_wrong_single(self):
        self._test_spoken_language(False, 'de', 'en')

    def test_list_rooms_spoken_country_wrong_multi(self):
        self._test_spoken_language(False, 'de', 'en,es')

    def test_list_rooms_spoken_country_allows_multi_user_none(self):
        self._test_spoken_language(False, 'de,en', None)

    def test_list_rooms_spoken_country_allows_multi_user_empty(self):
        self._test_spoken_language(False, 'de,en', '')

    def test_list_rooms_spoken_country_allows_multi_user_not_matching(self):
        self._test_spoken_language(False, 'de,en', 'es')

    def test_list_rooms_spoken_country_allows_multi_user_multi_none_matching(self):
        self._test_spoken_language(False, 'de,en', 'es,sv')

    def test_list_rooms_spoken_country_allows_multi_user_multi_none_matching_trailing(self):
        self._test_spoken_language(False, 'de,en', 'es,sv,')

    def test_list_rooms_spoken_country_same_single(self):
        self._test_spoken_language(True, 'de', 'de')

    def test_list_rooms_spoken_country_same_multi(self):
        self._test_spoken_language(True, 'de', 'de,en')

    def test_list_rooms_spoken_country_allows_multi_user_matching(self):
        self._test_spoken_language(True, 'de,en', 'en')

    def test_list_rooms_spoken_country_allows_multi_user_multi_matching_single(self):
        self._test_spoken_language(True, 'de,en', 'es,en')

    def test_list_rooms_spoken_country_allows_multi_user_multi_matching_single_reverse(self):
        self._test_spoken_language(True, 'de,en', 'en,es')

    def test_list_rooms_spoken_country_allows_multi_user_multi_matching_single_reverse_trailing(self):
        self._test_spoken_language(True, 'de,en', 'en,es,')

    def test_list_rooms_no_channel_id_status_code_false(self):
        self.assert_in_room(False)
        activity = self.activity_for_list_rooms()
        del activity['object']['url']
        is_valid, code, msg = request.on_list_rooms(as_parser(activity))
        self.assertFalse(is_valid)
        self.assertEqual(code, ErrorCodes.MISSING_OBJECT_URL)

    def test_list_rooms_status_code_true_if_no_rooms(self):
        self.assert_in_room(False)
        response_data = request.on_list_rooms(as_parser(self.activity_for_list_rooms()))
        self.assertEqual(True, response_data[0])

    def _test_spoken_language(self, should_succeed: bool, channel_lang, user_lang):
        self.assert_in_room(False)
        self.set_channel_acl({ApiActions.LIST: {'spoken_language': channel_lang}})
        self.set_session(SessionKeys.spoken_language.value, user_lang)

        activity = self.activity_for_list_rooms()
        is_valid, code, msg = request.on_list_rooms(as_parser(activity))

        if should_succeed:
            self.assertTrue(is_valid)
            self.assertIsNone(code)
        else:
            self.assertFalse(is_valid)
            self.assertEqual(code, ErrorCodes.NOT_ALLOWED)
