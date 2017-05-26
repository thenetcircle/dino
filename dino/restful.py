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
from flask_restful import Api

from dino.rest.resources.banned import BannedResource
from dino.rest.resources.ban import BanResource
from dino.rest.resources.kick import KickResource
from dino.rest.resources.roles import RolesResource
from dino.rest.resources.rooms_for_users import RoomsForUsersResource
from dino.rest.resources.remove_admin import RemoveAdminResource
from dino.rest.resources.set_admin import SetAdminResource
from dino.rest.resources.history import HistoryResource
from dino.rest.resources.clear_history import ClearHistoryResource
from dino.rest.resources.blacklist import BlacklistResource
from dino import environ
from dino.hooks import *

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


def create_app():
    _app = Flask(__name__)
    _app.config['SECRET_KEY'] = '945bd584-abd6-11e6-b2be-9b428bdb027f'
    _api = Api(_app)

    return _app, _api


app, api = create_app()

api.add_resource(ClearHistoryResource, '/delete-messages')
api.add_resource(RolesResource, '/roles')
api.add_resource(BannedResource, '/banned')
api.add_resource(BanResource, '/ban')
api.add_resource(HistoryResource, '/history')
api.add_resource(KickResource, '/kick')
api.add_resource(RoomsForUsersResource, '/rooms-for-users')
api.add_resource(SetAdminResource, '/set-admin')
api.add_resource(RemoveAdminResource, '/remove-admin')
api.add_resource(BlacklistResource, '/blacklist')
