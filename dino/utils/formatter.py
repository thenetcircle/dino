# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from zope.interface import Interface
from zope.interface import implementer

from dino.config import ErrorCodes

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class IResponseFormatter(Interface):
    def __call__(self, *args, **kwargs):
        """
        format the response from an api call based on the configured format

        :param args: index 0 is the status_code from ErrorCodes, index 1 is the data/error message
        :param kwargs: not used
        :return: a formatted response
        """


@implementer(IResponseFormatter)
class SimpleResponseFormatter(object):
    def __init__(self, code_key: str, data_key: str, error_key: str):
        self.code_key = code_key
        self.data_key = data_key
        self.error_key = error_key

    def __call__(self, *args, **kwargs):
        assert len(args) == 2
        status_code, data = args[0], args[1]

        if status_code != ErrorCodes.OK:
            return {self.code_key: status_code, self.error_key: data}
        return {self.code_key: status_code, self.data_key: data}

    def __repr__(self):
        return 'SimpleResponseFormatter<format="{%s: <status code>, %s: <data dict>, %s: <error message>}">' % \
               (self.code_key, self.data_key, self.error_key)
