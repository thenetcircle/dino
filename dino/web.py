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

from flask import Flask
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


def create_app():
    _app = Flask(
            import_name=__name__,
            template_folder='admin/templates/',
            static_folder='admin/static/')

    _app.config['SECRET_KEY'] = 'abc492ee-9739-11e6-a174-07f6b92d4a4b'

    return _app

app = create_app()

import dino.admin.routes
