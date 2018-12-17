from unittest import TestCase

from dino.config import ErrorCodes
from dino.utils.formatter import SimpleResponseFormatter


class DecoratorTest(TestCase):
    def test_format_ok(self):
        code_key = 'status_code'
        data_key = 'data'
        error_key = 'msg'

        formatter = SimpleResponseFormatter('status_code', 'data', 'msg')
        response = formatter(ErrorCodes.OK, 'some data')

        self.assertTrue(code_key in response.keys())
        self.assertTrue(data_key in response.keys())
        self.assertFalse(error_key in response.keys())
        self.assertEqual(ErrorCodes.OK, response.get(code_key))

    def test_format_not_ok(self):
        code_key = 'status_code'
        data_key = 'data'
        error_key = 'msg'

        formatter = SimpleResponseFormatter('status_code', 'data', 'msg')
        response = formatter(ErrorCodes.NOT_ALLOWED, 'some data')

        self.assertTrue(code_key in response.keys())
        self.assertFalse(data_key in response.keys())
        self.assertTrue(error_key in response.keys())
        self.assertEqual(ErrorCodes.NOT_ALLOWED, response.get(code_key))

    def test_repr(self):
        code_key = 'status_code'
        data_key = 'data'
        error_key = 'msg'

        formatter = SimpleResponseFormatter('status_code', 'data', 'msg')
        repr_str = formatter.__repr__()

        self.assertTrue(code_key in repr_str)
        self.assertTrue(data_key in repr_str)
        self.assertTrue(error_key in repr_str)
