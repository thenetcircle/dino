class MockDatabase(object):
    def __init__(self):
        self.Session = FakeSession()


class FakeSession(object):
    pass
