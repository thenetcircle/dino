from unittest import TestCase

from dino.environ import GNEnvironment, ConfigDict
from dino.utils.spam import SpamClassifier


class FakeServiceConfig(object):
    def __init__(self, threshold, min_length, max_length):
        self.threshold = threshold
        self.min_length = min_length
        self.max_length = max_length

    def get_spam_threshold(self):
        return self.threshold

    def get_spam_min_length(self):
        return self.min_length

    def get_spam_max_length(self):
        return self.max_length


class FakeEnv(GNEnvironment):
    def __init__(self, threshold, min_length, max_length):
        super().__init__('.', ConfigDict(), skip_init=True)
        self.service_config = FakeServiceConfig(threshold, min_length, max_length)


class TestSpam(TestCase):
    def test_too_short(self):
        self.env = FakeEnv(80, 10, 30)
        self.spam = SpamClassifier(self.env, skip_loading=True)
        self.assertTrue(self.spam.too_long_or_too_short('a' * 5))

    def test_too_long(self):
        self.env = FakeEnv(80, 10, 30)
        self.spam = SpamClassifier(self.env, skip_loading=True)
        self.assertTrue(self.spam.too_long_or_too_short('a' * 35))

    def test_okay_length(self):
        self.env = FakeEnv(80, 10, 30)
        self.spam = SpamClassifier(self.env, skip_loading=True)
        self.assertFalse(self.spam.too_long_or_too_short('a' * 20))

    def test_is_spam(self):
        threshold = 0.8
        self.env = FakeEnv(threshold, 20, 150)
        self.spam = SpamClassifier(self.env)

        is_spam, y_hats = self.spam.is_spam(
            '[̲̅G̲̅][̲̅u̲̅][̲̅t̲̅][̲̅e̲̅][̲̅n̲̅] [̲̅M̲̅][̲̅o̲̅][̲̅r̲̅][̲̅g̲̅]a[̲̅h̲̅][̲̅n̲̅]'
        )

        above = 0
        for y_hat in y_hats:
            if y_hat > threshold:
                above += 1

        self.assertTrue(is_spam)
        self.assertTrue(above >= 2)
