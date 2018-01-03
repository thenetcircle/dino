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

import logging
import os
import traceback
import requests
from typing import List
from typing import Union
from uuid import uuid4 as uuid
from functools import wraps

from flask import jsonify
from flask import render_template
from flask import request
from flask import redirect
from flask import send_from_directory
from git.cmd import Git
from flask_oauthlib.client import OAuth
from werkzeug.wrappers import Response

from dino import environ
from dino import utils
from dino.admin.orm import acl_manager
from dino.admin.orm import blacklist_manager
from dino.admin.orm import broadcast_manager
from dino.admin.orm import channel_manager
from dino.admin.orm import room_manager
from dino.admin.orm import storage_manager
from dino.admin.orm import user_manager
from dino.config import ApiTargets
from dino.config import ConfigKeys
from dino.exceptions import ChannelNameExistsException
from dino.exceptions import EmptyChannelNameException
from dino.exceptions import InvalidAclTypeException
from dino.exceptions import InvalidAclValueException
from dino.exceptions import NoSuchUserException
from dino.exceptions import UnknownBanTypeException
from dino.exceptions import ValidationException
from dino.web import app

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

acl_config = environ.env.config.get(ConfigKeys.ACL)

home_dir = os.environ.get('DINO_HOME', default=None)
environment = os.environ.get('DINO_ENVIRONMENT', default=None)

if home_dir is None:
    home_dir = '.'
tag_name = Git(home_dir).describe()

def is_blank(s: str):
    return s is None or len(s.strip()) == 0


def api_response(code, data: Union[dict, List[dict]]=None, message: Union[dict, str]=None):
    if data is None:
        data = dict()
    if message is None:
        message = ''

    return jsonify({
        'status_code': code,
        'data': data,
        'message': message
    })

def internal_url_for(url):
    return app.config['ROOT_URL'] + url

############################
#           SSO            #
############################
oauth = OAuth(app)
SERVICE_ID = 'ChatService'
DOMAIN = 'http://services.ideawise.lab'
UNAUTHORIZED_PAGE = DOMAIN + "/unauthorized"
OAUTH_SERVER = DOMAIN + "/sso-oauth/rest/v1/oauth"
AUTHORIZE_URL = OAUTH_SERVER + "/auth/authorize"
TOKEN_URL = OAUTH_SERVER + "/access-tokens/issue"
CALLBACK_URL = DOMAIN + app.config['ROOT_URL'] + '/login/callback'

# FOR DEV MODE (can use http to authenticate)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'

chat = oauth.remote_app(
    SERVICE_ID,
    consumer_key=SERVICE_ID,
    consumer_secret=SERVICE_ID,
    base_url=OAUTH_SERVER,
    request_token_params={},
    request_token_url=None,
    access_token_method='POST',
    access_token_url=TOKEN_URL,
    authorize_url=AUTHORIZE_URL
)

def parse_services(services):
    parsed = list()
    for service in services:
        parsed.append(service['name'].split(',')[0].split('=')[1])
    return parsed

def check(token):
    resp = requests.post(OAUTH_SERVER + "/access-tokens/check?access_token=" + token)
    if resp.status_code >= 200 and resp.status_code < 399:
        try:
            content = resp.json()
            services = parse_services(content['scopes'])
            if SERVICE_ID not in services:
                return redirect(UNAUTHORIZED_PAGE)
        except Exception:
            return False
        return True
    return False

def is_authorized():
    if 'token' not in request.cookies:
        return False
    return check(request.cookies.get('token'))

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        state = is_authorized()
        # Invalid Access
        if state is False:
            # For api
            if request.path.startswith('/api'):
                return api_response(400, message="Invalid authentication.")
            # For 
            return redirect(internal_url_for('/login'))
        # No accessibility to chat service
        if isinstance(state, Response):
            return state

        return f(*args, **kwargs)
    return decorated


@app.route('/login')
def login():
    return chat.authorize(callback=CALLBACK_URL)


@app.route('/logout')
def logout():
    request.cookies.pop('token', None)
    return redirect(internal_url_for('/login'))

@app.route('/login/callback')
def authorized():
    resp = chat.handle_oauth2_response()
    if resp is None or resp.get('access_token') is None:
        return 'Access denied: reason=%s error=%s resp=%s' % (
            request.args['error'],
            request.args['error_description'],
            resp
        )
    response = redirect(internal_url_for('/index'))
    response.set_cookie('token', resp['access_token'])
    return response

@chat.tokengetter
def get_sso_token():
    return request.cookies.get('token')


@app.route('/', methods=['GET'])
@requires_auth
def index():
    return render_template(
        'index.html',
        environment=environment,
        config={
            'ROOT_URL': environ.env.config.get(ConfigKeys.ROOT_URL, domain=ConfigKeys.WEB)
        },
        version=tag_name)


####################################
#             Channels             #
####################################
@app.route('/api/channels', methods=['GET'])
@requires_auth
def channels():
    """ Get all channels. """
    return api_response(200, channel_manager.get_channels())


@app.route('/api/channels', methods=['POST'])
@requires_auth
def create_channel():
    """ Create new channel """
    form = request.get_json()
    channel_name = form['name']
    channel_uuid = str(uuid())
    user_uuid = form['owner']
    
    message = {}
    if is_blank(channel_name):
        message['name'] = "Channel name can't be none."
    if is_blank(user_uuid):
        message['owner'] = "Owner can't be none."
    
    if len(message):
        return api_response(400, message=message)
    result = channel_manager.create_channel(channel_name, channel_uuid, user_uuid)

    if result is not None:
        return api_response(400, message=result)
    return api_response(200, {'sort': 1, 'name': channel_name, 'uuid': channel_uuid})


@app.route('/api/channels/<channel_uuid>', methods=['DELETE'])
@requires_auth
def delete_channel(channel_uuid: str):
    channel_manager.remove_channel(channel_uuid)
    return api_response(200)


@app.route('/api/channels/<channel_uuid>/name', methods=['PUT'])
@requires_auth
def update_channel_name(channel_uuid: str):
    form = request.get_json()
    name = form['name']

    try:
        channel_manager.rename(channel_uuid, name)
    except ChannelNameExistsException:
        return api_response(400, message='A channel with that name already exists')
    except EmptyChannelNameException:
        return api_response(400, message='Blank channel name is not allowed')

    return api_response(200)


@app.route('/api/channels/<channel_uuid>/order', methods=['PUT'])
@requires_auth
def update_channel_order(channel_uuid: str):
    form = request.get_json()
    order = form['order']
    channel_manager.update_sort(channel_uuid, order)
    return api_response(200)


@app.route('/api/channels/<channel_uuid>', methods=['GET'])
@requires_auth
def get_channel(channel_uuid: str):
    """ Get channel owners/admins/acls """
    acls = acl_manager.get_acls_channel(channel_uuid)
    acls_decoded = list()
    for acl in acls:
        acl['value'] = utils.b64d(acl['value'])
        acls_decoded.append(acl)

    return api_response(200, {
        'owners': channel_manager.get_owners(channel_uuid),
        'admins': channel_manager.get_admins(channel_uuid),
        'acls': acls_decoded,
    })


@app.route('/api/channels/<channel_uuid>/owners', methods=['POST'])
@requires_auth
def add_channel_owner(channel_uuid: str):
    form = request.get_json()
    user_uuid = form['owner']

    if is_blank(user_uuid):
        return api_response(400, message='Blank user id is not allowed')

    try:
        user = user_manager.get_user(user_uuid)
        user['name'] = utils.b64d(user['name'])
    except NoSuchUserException:
        return api_response(400, message='No Such User.')

    user_manager.add_channel_owner(channel_uuid, user_uuid)
    return api_response(200, user)


@app.route('/api/channels/<channel_uuid>/owners/<user_uuid>', methods=['DELETE'])
@requires_auth
def remove_channel_owner(channel_uuid: str, user_uuid: str):
    user_manager.remove_channel_owner(channel_uuid, user_uuid)
    return api_response(200)


@app.route('/api/channels/<channel_uuid>/admins', methods=['POST'])
@requires_auth
def add_channel_admin(channel_uuid: str):
    form = request.get_json()
    user_uuid = form['admin']

    if is_blank(user_uuid):
        return api_response(400, message='Blank user id is not allowed.')
    try:
        user = user_manager.get_user(user_uuid)
        user['name'] = utils.b64d(user['name'])
    except NoSuchUserException:
        return api_response(400, message='No Such User.')
    user_manager.add_channel_admin(channel_uuid, user_uuid)
    return api_response(200, user)


@app.route('/api/channels/<channel_uuid>/admins/<user_uuid>', methods=['DELETE'])
@requires_auth
def remove_channel_admin(channel_uuid: str, user_uuid: str):
    user_manager.remove_channel_admin(channel_uuid, user_uuid)
    return api_response(200)


@app.route('/api/channels/<channel_uuid>/acls', methods=['POST'])
@requires_auth
def create_channel_acl(channel_uuid: str):
    form = request.get_json()
    action = form['action']
    acl_type = form['type']
    acl_value = form['value']

    message = {}
    if is_blank(acl_type):
        message['type'] = 'Blank type is not allowed.'
    if is_blank(acl_value):
        message['value'] = 'Blank value is not allowed.'
    if len(message):
        return api_response(400, message=message)

    try:
        acl_manager.add_acl_channel(channel_uuid, action, acl_type, acl_value)
    except InvalidAclValueException:
        return api_response(400, message='Invalid ACL value %s' % acl_value)
    except InvalidAclTypeException:
        return api_response(400, message='Invalid ACL type %s' % acl_type)
    except ValidationException as e:
        return api_response(400, message='Invalid ACL: %s' % e.msg)
    except Exception as e:
        logger.exception(traceback.format_exc())
        return api_response(400, message='could not create acl for channel %s: %s' % (channel_uuid, str(e)))
    
    return api_response(200)


@app.route('/api/channels/<channel_uuid>/acls/<action>/<acl_type>', methods=['PUT'])
@requires_auth
def update_channel_acl(channel_uuid: str, action: str, acl_type: str):
    form = request.get_json()
    value = form['value']
    
    try:
        acl_manager.update_channel_acl(channel_uuid, action, acl_type, value)
    except InvalidAclValueException:
        return api_response(400, message='Invalid ACL value %s' % value)
    except InvalidAclTypeException:
        return api_response(400, message='Invalid ACL type %s' % acl_type)
    except ValidationException as e:
        return api_response(400, message='Invalid ACL: %s' % e.msg)
    except Exception as e:
        logger.exception(traceback.format_exc())
        return api_response(400, message='could not update acl for channel %s: %s' % (channel_uuid, str(e)))
    
    return api_response(200)


@app.route('/api/channels/<channel_uuid>/acls/<action>/<acl_type>', methods=['DELETE'])
@requires_auth
def delete_channel_acl(channel_uuid: str, action: str, acl_type: str):
    acl_manager.delete_acl_channel(channel_uuid, action, acl_type)
    return api_response(200)


####################################
#               Rooms              #
####################################
@app.route('/api/channels/<channel_uuid>/rooms', methods=['GET'])
@requires_auth
def rooms_for_channel(channel_uuid: str):
    """ Get rooms of channel """
    return api_response(200, room_manager.get_rooms(channel_uuid))


@app.route('/api/channels/<channel_uuid>/rooms', methods=['POST'])
@requires_auth
def create_room(channel_uuid: str):
    form = request.get_json()
    room_name = form['name']
    room_uuid = str(uuid())
    user_uuid = form['owner']
    
    message = {}
    if is_blank(room_name):
        message['name'] = 'Blank room name is not allowed.'
    if is_blank(user_uuid):
        message['owner'] = 'Blank owner is not allowed.'
    
    if len(message):
        return api_response(400, message=message)
    try:
        result = room_manager.create_room(room_name, room_uuid, channel_uuid, user_uuid)
        if result is not None:
            return api_response(400, message=result)
        
        return api_response(200, { 
            'sort': 10, 
            'name': room_name, 
            'uuid': room_uuid,
            'is_admin': False,
            'is_default': False,
            'is_ephemeral': False,
        })
    except NoSuchUserException:
        return api_response(400, message={
            'owner': 'No such user',
        })


@app.route('/api/rooms/<room_uuid>/order', methods=['PUT'])
@requires_auth
def update_room_order(room_uuid: str):
    form = request.get_json()
    order = form['order']
    room_manager.update_sort(room_uuid, order)
    return api_response(200)


@app.route('/api/channels/<channel_uuid>/rooms/<room_uuid>/name', methods=['PUT'])
@requires_auth
def update_room_name(channel_uuid: str, room_uuid: str):
    form = request.get_json()
    name = form['name']

    result = room_manager.rename(channel_uuid, room_uuid, name)
    if result is not None:
        return api_response(400, message=result)
    return api_response(200)


@app.route('/api/channels/<channel_uuid>/rooms/<room_uuid>', methods=['GET'])
@requires_auth
def get_room(channel_uuid: str, room_uuid: str):
    acls = acl_manager.get_acls_room(room_uuid)
    acls_decoded = list()
    for acl in acls:
        acl['value'] = utils.b64d(acl['value'])
        acls_decoded.append(acl)
    
    return api_response(200, {
        'channel': {
            'uuid': channel_uuid,
            'name': channel_manager.name_for_uuid(channel_uuid)
        },
        'acls': acls_decoded,
        'owners': room_manager.get_owners(room_uuid),
        'moderators': room_manager.get_moderators(room_uuid)
    })


@app.route('/api/rooms/<room_uuid>/set-default', methods=['PUT'])
@requires_auth
def set_default_room(room_uuid: str):
    try:
        room_manager.set_default_room(room_uuid)
    except Exception as e:
        logger.error('Could not set room as default: %s' % str(e))
        return api_response(400, message='Could not set room as default: %s' % str(e))
    return api_response(200)


@app.route('/api/rooms/<room_uuid>/unset-default', methods=['PUT'])
@requires_auth
def unset_default_room(room_uuid: str):
    try:
        room_manager.unset_default_room(room_uuid)
    except Exception as e:
        logger.error('Could not set room as default: %s' % str(e))
        return api_response(400, message='Could not set room as default: %s' % str(e))
    return api_response(200)


@app.route('/api/rooms/<room_uuid>/set-ephemeral', methods=['PUT'])
@requires_auth
def set_ephemeral_room(room_uuid: str):
    """ Set as ephemeral room """
    try:
        room_manager.set_ephemeral_room(room_uuid)
    except Exception as e:
        logger.error('Could not set room as ephemeral: %s' % str(e))
        return api_response(400, message='Could not set room as ephemeral: %s' % str(e))
    return api_response(200)


@app.route('/api/rooms/<room_uuid>/unset-ephemeral', methods=['PUT'])
@requires_auth
def unset_ephemeral_room(room_uuid: str):
    try:
        room_manager.unset_ephemeral_room(room_uuid)
    except Exception as e:
        logger.error('Could not set room as ephemeral: %s' % str(e))
        return api_response(400, message='Could not set room as ephemeral: %s' % str(e))
    return api_response(200)


@app.route('/api/rooms/<room_uuid>/set-admin', methods=['PUT'])
@requires_auth
def set_admin_room(room_uuid: str):
    try:
        room_manager.set_admin_room(room_uuid)
    except Exception as e:
        logger.error('Could not set room as admin: %s' % str(e))
        return api_response(400, message='Could not set room as admin: %s' % str(e))
    return api_response(200)


@app.route('/api/rooms/<room_uuid>/unset-admin', methods=['PUT'])
@requires_auth
def unset_admin_room(room_uuid: str):
    try:
        room_manager.unset_admin_room(room_uuid)
    except Exception as e:
        logger.error('Could not set room as admin: %s' % str(e))
        return api_response(400, message='Could not set room as admin: %s' % str(e))
    return api_response(200)


@app.route('/api/channels/<channel_uuid>/rooms/<room_uuid>', methods=['DELETE'])
@requires_auth
def delete_room(channel_uuid: str, room_uuid: str):
    room_manager.remove_room(channel_uuid, room_uuid)
    return api_response(200)


@app.route('/api/rooms/<room_uuid>/owners', methods=['POST'])
@requires_auth
def add_room_owner(room_uuid: str):
    form = request.get_json()
    user_uuid = form['owner']

    if is_blank(user_uuid):
        return api_response(400, message='Blank user id is not allowed')

    try:
        user = user_manager.get_user(user_uuid)
        user['name'] = utils.b64d(user['name'])
    except NoSuchUserException:
        return api_response(400, message='No Such User.')

    user_manager.add_room_owner(room_uuid, user_uuid)
    return api_response(200, user)


@app.route('/api/rooms/<room_uuid>/owners/<user_uuid>', methods=['DELETE'])
@requires_auth
def delete_room_owner(room_uuid: str, user_uuid: str):
    user_manager.remove_room_owner(room_uuid, user_uuid)
    return api_response(200)


@app.route('/api/rooms/<room_uuid>/moderators', methods=['POST'])
@requires_auth
def add_room_moderator(room_uuid: str):
    form = request.get_json()
    user_uuid = form['moderator']

    if is_blank(user_uuid):
        return api_response(400, message='Blank user id is not allowed.')
    try:
        user = user_manager.get_user(user_uuid)
        user['name'] = utils.b64d(user['name'])
    except NoSuchUserException:
        return api_response(400, message='No Such User.')
    user_manager.add_room_moderator(room_uuid, user_uuid)
    return api_response(200, user)


@app.route('/api/rooms/<room_uuid>/moderators/<user_uuid>', methods=['DELETE'])
@requires_auth
def delete_room_moderator(room_uuid: str, user_uuid: str):
    user_manager.remove_room_moderator(room_uuid, user_uuid)
    return api_response(200)


@app.route('/api/rooms/<room_uuid>/acls', methods=['POST'])
@requires_auth
def create_room_acl(room_uuid: str):
    form = request.get_json()
    action = form['action']
    acl_type = form['type']
    acl_value = form['value']

    message = {}
    if is_blank(action):
        message['action'] = 'Blank action is not allowed.'
    if is_blank(acl_type):
        message['type'] = 'Blank type is not allowed.'
    if is_blank(acl_value):
        message['value'] = 'Blank value is not allowed.'
    if len(message):
        return api_response(400, message=message)

    try:
        acl_manager.add_acl_room(room_uuid, action, acl_type, acl_value)
    except InvalidAclValueException:
        return api_response(400, message='Invalid ACL value %s' % acl_value)
    except InvalidAclTypeException:
        return api_response(400, message='Invalid ACL type %s' % acl_type)
    except ValidationException as e:
        return api_response(400, message='Invalid ACL: %s' % e.msg)
    except Exception as e:
        logger.exception(traceback.format_exc())
        return api_response(400, message='could not create acl for room %s: %s' % (room_uuid, str(e)))
    
    return api_response(200)


@app.route('/api/channels/<channel_uuid>/rooms/<room_uuid>/acls/<action>/<acl_type>', methods=['PUT'])
@requires_auth
def update_room_acl(channel_uuid: str, room_uuid: str, action: str, acl_type: str):
    form = request.get_json()
    value = form['value']
    
    try:
        acl_manager.update_room_acl(channel_uuid, room_uuid, action, acl_type, value)
    except InvalidAclValueException:
        return api_response(400, message='Invalid ACL value %s' % value)
    except InvalidAclTypeException:
        return api_response(400, message='Invalid ACL type %s' % acl_type)
    except ValidationException as e:
        return api_response(400, message='Invalid ACL: %s' % e.msg)
    except Exception as e:
        logger.exception(traceback.format_exc())
        return api_response(400, message='could not update acl for room %s: %s' % (room_uuid, str(e)))
    
    return api_response(200)


@app.route('/api/rooms/<room_uuid>/acls/<action>/<acl_type>', methods=['DELETE'])
@requires_auth
def delete_room_acl(room_uuid: str, action: str, acl_type: str):
    acl_manager.delete_acl_room(room_uuid, action, acl_type)
    return api_response(200)


####################################
#               Users              #
####################################


@app.route('/api/rooms/<room_uuid>/users', methods=['GET'])
@requires_auth
def get_users_for_room(room_uuid: str):
    return api_response(200, user_manager.get_users_for_room(room_uuid))


@app.route('/api/users/<user_uuid>', methods=['GET'])
@requires_auth
def get_user(user_uuid: str):
    try:
        user = user_manager.get_user(user_uuid)
    except NoSuchUserException:
        return api_response(400, message='No Such User.')
    return api_response(200, user)


@app.route('/api/rooms/<room_uuid>/users/<user_uuid>/kick', methods=['POST'])
@requires_auth
def kick_user(room_uuid: str, user_uuid: str):
    try:
        user_manager.kick_user(room_uuid, user_uuid)
    except Exception as e:
        logger.error('Could not kick user %s' % str(e))
        return api_response(400, message='Could not kick user %s' % str(e))
    return api_response(200)


@app.route('/api/bans', methods=['GET'])
@requires_auth
def banned_users():
    bans = user_manager.get_banned_users()
    result = {'global': list(), 'channel': list(), 'room': list()}

    channel_bans = bans['channels']
    for channel_id in channel_bans:
        channel = {'name': utils.b64d(channel_bans[channel_id]['name']), 'uuid': channel_id}
        for user_id in channel_bans[channel_id]['users']:
            user = channel_bans[channel_id]['users'][user_id]
            user['uuid'] = user_id
            user['name'] = utils.b64d(user['name'])
            user['channel'] = channel
            result['channel'].append(user)
            
    room_bans = bans['rooms']
    for room_id in room_bans:
        room = {'name': utils.b64d(room_bans[room_id]['name']), 'uuid': room_id}
        for user_id in room_bans[room_id]['users']:
            user = room_bans[room_id]['users'][user_id]
            user['uuid'] = user_id
            user['name'] = utils.b64d(user['name'])
            user['room'] = room
            result['room'].append(user)
            
    global_bans = bans['global']
    for user_id in global_bans:
            user = global_bans[user_id]
            user['uuid'] = user_id
            user['name'] = utils.b64d(user['name'])
            result['global'].append(user)
    return api_response(200, result)


@app.route('/api/bans', methods=['POST'])
@requires_auth
def ban_user():
    form = request.get_json()
    target = form['target']
    target_uuid = form['target_uuid']
    user_uuid = form['user_uuid']
    duration = form['duration']

    try:
        user_manager.ban_user(user_uuid, target_uuid, duration, target)
    except ValidationException as e:
        return api_response(400, message='invalid duration: %s' % str(e))
    except UnknownBanTypeException as e:
        return api_response(400, message='could not ban user: %s' % str(e))
    except Exception as e:
        logger.exception(traceback.format_exc())
        return api_response(400, message=str(e))

    try:
        user = user_manager.get_user(user_uuid)
        user['name'] = utils.b64d(user['name'])
        user['duration'] = duration
    except NoSuchUserException:
        return api_response(400, message="No such user.")

    if target == 'channel':
        user['channel'] = {
            'uuid': target_uuid,
            'name': channel_manager.name_for_uuid(target_uuid)
        }
    elif target == 'room':
        user['room'] = {
            'uuid': target_uuid,
            'name': room_manager.name_for_uuid(target_uuid)
        }
    return api_response(200, user)


@app.route('/api/bans/<user_uuid>/delete', methods=['POST'])
@requires_auth
def remove_ban(user_uuid: str):
    form = request.get_json()
    target = form['target']
    target_uuid = form['target_uuid']
    user_manager.remove_ban(user_uuid, target_uuid, target)
    return api_response(200)


####################################
#           Super Users            #
####################################


@app.route('/api/super-users', methods=['GET'])
@requires_auth
def super_users():
    return api_response(200, user_manager.get_super_users())


@app.route('/api/super-users', methods=['POST'])
@requires_auth
def create_super_user():
    form = request.get_json()
    user_name = str(form['name']).strip()
    user_uuid = str(form['uuid']).strip()

    message = {}
    if is_blank(user_name):
        message['name'] = 'Blank user name is not allowed.'
    if is_blank(user_uuid):
        message['uuid'] = 'Blank user id is not allowed.'

    if len(message):
        return api_response(400, message=message)
    user_manager.create_super_user(user_name, user_uuid)
    return api_response(200)


@app.route('/api/super-users/<user_uuid>', methods=['POST'])
@requires_auth
def set_super_user(user_uuid: str):
    user_manager.set_super_user(user_uuid)
    return api_response(200)


@app.route('/api/super-users/<user_uuid>', methods=['DELETE'])
@requires_auth
def remove_super_user(user_uuid: str):
    user_manager.del_super_user(user_uuid)
    return api_response(200)


@app.route('/api/users/search/<query>', methods=['GET'])
@requires_auth
def search_user(query: str):
    return api_response(200, user_manager.search_for(query))


####################################
#             History              #
####################################


@app.route('/api/history', methods=['POST'])
@requires_auth
def search_history():
    form = request.get_json()
    user_uuid = form['user']
    room_uuid = form['room']
    from_time = form['from']
    to_time = form['to']

    try:
        msgs, real_from_time, real_to_time = storage_manager.find_history(room_uuid, user_uuid, from_time, to_time)
    except Exception as e:
        logger.error('Could not get messages: %s' % str(e))
        logger.exception(traceback.format_exc())
        return api_response(400, message='Could not get message: %s' % str(e))

    if real_from_time is not None:
        real_from_time = real_from_time.strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
    if real_to_time is not None:
        real_to_time = real_to_time.strftime(ConfigKeys.DEFAULT_DATE_FORMAT)

    return api_response(200, {
        'message': msgs,
        'real_from_time': real_from_time,
        'real_to_time': real_to_time,
    })


@app.route('/api/history/<message_id>', methods=['DELETE'])
@requires_auth
def delete_message(message_id: str):
    storage_manager.delete_message(message_id)
    return api_response(200)


@app.route('/api/history/<message_id>/undelete', methods=['PUT'])
@requires_auth
def undo_delete_message(message_id: str):
    storage_manager.undelete_message(message_id)
    return api_response(200)


####################################
#            Blacklist             #
####################################


@app.route('/api/blacklist', methods=['GET'])
@requires_auth
def blacklist():
    return api_response(200, blacklist_manager.get_black_list())


@app.route('/api/blacklist', methods=['POST'])
@requires_auth
def add_to_blacklist():
    form = request.get_json()
    words = form['words']
    try:
        blacklist_manager.add_words(words)
    except Exception as e:
        logger.error('Could not add word to blacklist: %s' % str(e))
        return api_response(400, message='Could not add word to blacklist: %s' % str(e))
    return api_response(200)


@app.route('/api/blacklist/<word_id>', methods=['DELETE'])
@requires_auth
def remove_from_blacklist(word_id: str):
    try:
        blacklist_manager.remove_word(word_id)
    except Exception as e:
        logger.error('Could not remove word from blacklist: %s' % str(e))
        return api_response(400, message='Could not remove word from blacklist: %s' % str(e))
    return api_response(200)


@app.route('/api/broadcast', methods=['POST'])
@requires_auth
def send_broadcast():
    form = request.get_json()
    verb = form['verb']
    content = form['content']

    message = {}
    if is_blank(verb):
        message['verb'] = 'Verb may not be empty.'
    if is_blank(content):
        message['content'] = 'Content may not be empty.'

    if len(message):
        return api_response(400, message=message)

    try:
        content = utils.b64e(content)
        broadcast_manager.send(content, verb)
    except Exception as e:
        logger.error('Could not send broadcast: %s' % str(e))
        logger.exception(traceback.format_exc())
        return api_response(400, message='Could not send broadcast')
    return api_response(200)


@app.route('/api/acls/<target>/actions/<api_action>/types', methods=['GET'])
@requires_auth
def acl_types_for_target_and_action(target: str, api_action: str):
    if target not in [ApiTargets.CHANNEL, ApiTargets.ROOM]:
        return api_response(400, message='unknown target type "%s"' % target)

    config = acl_config[target][api_action]
    acls = set(config['acls'])
    excludes = set()
    if 'exclude' in config:
        excludes = set(config['exclude'])

    output = list()
    for acl in acls:
        if acl in excludes:
            continue

        output.append({
            'acl_type': acl,
            'name': acl.capitalize()
        })
    return api_response(200, output)


@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('admin/static/', path)


@app.errorhandler(404)
def page_not_found(e):
    # your processing here
    return redirect(internal_url_for('/'))
