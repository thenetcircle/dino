#!/usr/bin/env python

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

import signal

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class GracefulInterruptHandler(object):
    def __init__(self, sig=signal.SIGINT):
        self.sig = sig
        self.interrupted = False
        self.released = False
        self.original_handler = None

    def __enter__(self):
        self.interrupted = False
        self.released = False
        self.original_handler = signal.getsignal(self.sig)

        def handler(signum, frame):
            self.release()
            self.interrupted = True

        try:
            signal.signal(self.sig, handler)
        except ValueError:
            # when testing we can't use signal, just ignore
            pass

        return self

    def __exit__(self, type, value, tb):
        self.release()

    def release(self):
        if self.released:
            return False

        try:
            signal.signal(self.sig, self.original_handler)
        except ValueError:
            # when testing we can't use signal, just ignore
            pass

        self.released = True
        return True
