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
from flask_restful import Api

from dino.rest.resources.banned import BannedResource
from dino.rest.resources.rooms_for_users import RoomsForUsersResource

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


def create_app():
    _app = Flask(__name__)
    _app.config['SECRET_KEY'] = '0e6319d0-b83b-11e6-8621-c73910823497'
    _api = Api(_app)

    return _app, _api


app, api = create_app()

api.add_resource(BannedResource, '/banned')
api.add_resource(RoomsForUsersResource, '/rooms-for-users')
