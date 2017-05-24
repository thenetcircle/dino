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

import eventlet

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

# need to monkey patch some standard functions in python since they don't natively support async mode
eventlet.monkey_patch()

# keep this import; even though unused, gunicorn needs it, otherwise it will not start
from dino.restful import app

from dino import environ
environ.env.node = __name__
