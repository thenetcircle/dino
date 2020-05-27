from abc import ABC


class IStats(ABC):
    def incr(self, key: str) -> None:
        """
        increment a key

        :param key: the key to increment
        :return: nothing
        """

    def decr(self, key: str) -> None:
        """
        decrement a key

        :param key: the key to decrement
        :return: nothing
        """

    def timing(self, key: str, ms: int):
        """
        record an execution time for this key

        :param key: the key to report for
        :param ms: the timing in milliseconds
        :return: nothing
        """

    def gauge(self, key: str, value: int):
        """
        gauge a value

        :param key: the key to gauge for
        :param value: the gauged value
        :return: nothing
        """
