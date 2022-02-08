import os
import logging

from dino.utils import suppress_stdout_stderr
from dino.environ import GNEnvironment
from dino.utils.decorators import timeit

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


class SpamClassifier(object):
    def __init__(self, env: GNEnvironment, skip_loading: bool=False):
        from scipy import sparse
        from sklearn.externals import joblib

        self.sparse = sparse
        self.env = env

        if skip_loading:
            return

        root_path = env.root_path
        if root_path == '':
            root_path = '.'

        logger.info('loading TF-IDF and PCA transformers...')
        with suppress_stdout_stderr():
            self.tfidf_char = joblib.load(root_path + '/models/transformer_1a.pkl')
            self.tfidf_word = joblib.load(root_path + '/models/transformer_1b.pkl')
            self.pca = joblib.load(root_path + '/models/transformer_2.pkl')

        logger.info('loading models...')
        with suppress_stdout_stderr():
            self.xgb = joblib.load(root_path + '/models/classifier_1.pkl')
            self.rfc = joblib.load(root_path + '/models/classifier_2.pkl')
            self.svc = joblib.load(root_path + '/models/classifier_3.pkl')

        size = (
            os.path.getsize(root_path + '/models/transformer_1a.pkl') +
            os.path.getsize(root_path + '/models/transformer_1b.pkl') +
            os.path.getsize(root_path + '/models/transformer_2.pkl') +
            os.path.getsize(root_path + '/models/classifier_1.pkl') +
            os.path.getsize(root_path + '/models/classifier_2.pkl') +
            os.path.getsize(root_path + '/models/classifier_3.pkl')
        )
        logger.info('done loading, memory size: {} MB'.format('%.2f' % (size / 1024 / 1024)))

    @timeit(logger, 'on_transform')
    def transform(self, x):
        x = self.sparse.hstack((self.tfidf_char.transform(x), self.tfidf_word.transform(x))).A
        return self.pca.transform(x)

    @timeit(logger, 'on_predict')
    def predict(self, x):
        y_hat = (
            self.xgb.predict_proba(x)[0][1],
            self.rfc.predict_proba(x)[0][1],
            self.svc.predict(x)[0]
        )
        threshold = float(self.env.service_config.get_spam_threshold()) / 100

        # if 2 out of 3 classifiers are at least 'threshold' % certain it's spam, classify it as such
        return 1 if sum(1 for e in y_hat if e > threshold) >= 2 else 0, y_hat

    def is_spam(self, message) -> (bool, tuple):
        if self.too_long_or_too_short(message):
            return False, None

        x = self.transform([message])
        return self.predict(x)

    def too_long_or_too_short(self, message) -> bool:
        min_len = self.env.service_config.get_spam_min_length()
        max_len = self.env.service_config.get_spam_max_length()

        # short or overly long messages are usually not spam, and the models weren't trained on it
        return len(message) < min_len or len(message) > max_len
