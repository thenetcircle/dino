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

from flask import redirect
from flask import jsonify
from flask import request
from flask import send_from_directory
from flask import render_template
from uuid import uuid4 as uuid

import logging
import traceback

from dino import environ
from dino.config import ConfigKeys
from dino.config import ApiTargets

from dino.web import app
from dino.admin.orm import channel_manager
from dino.admin.orm import room_manager
from dino.admin.orm import acl_manager
from dino.admin.orm import user_manager

from dino.validation.acl import AclValidator
from dino.exceptions import InvalidAclValueException
from dino.exceptions import InvalidAclTypeException
from dino.exceptions import RoomNameExistsForChannelException
from dino.exceptions import ChannelNameExistsException
from dino.exceptions import EmptyChannelNameException
from dino.exceptions import EmptyRoomNameException
from dino.exceptions import UnknownBanTypeException
from dino.exceptions import ValidationException

from dino.admin.forms import CreateChannelForm
from dino.admin.forms import CreateRoomForm
from dino.admin.forms import CreateUserForm
from dino.admin.forms import CreateChannelAclForm
from dino.admin.forms import CreateRoomAclForm
from dino.admin.forms import AddModeratorForm
from dino.admin.forms import AddOwnerForm
from dino.admin.forms import AddAdminForm
from dino.admin.forms import BanForm

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

acl_config = environ.env.config.get(ConfigKeys.ACL)


def is_blank(s: str):
    return s is None or len(s.strip()) == ''


@app.route('/', methods=['GET'])
def index():
    return render_template('home.html')


@app.route('/channels', methods=['GET'])
def channels():
    form = CreateChannelForm(request.form)
    return render_template(
            'channels.html',
            form=form,
            channels=channel_manager.get_channels())


@app.route('/acl/<target>/action/<api_action>/types', methods=['GET'])
def acl_types_for_target_and_action(target: str, api_action: str):
    if target not in [ApiTargets.CHANNEL, ApiTargets.ROOM]:
        return jsonify({'status_code': 400, 'message': 'unknown target type "%s"' % target})

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
    return jsonify(output)


@app.route('/channel/<channel_uuid>/room/<room_uuid>/user/<user_uuid>/kick', methods=['PUT'])
def kick_user(channel_uuid: str, room_uuid: str, user_uuid: str):
    try:
        user_manager.kick_user(room_uuid, user_uuid)
    except Exception as e:
        logger.error('could not kick user: %s' % str(e))
        return jsonify({'status_code': 500, 'message': str(e)})
    return jsonify({'status_code': 200})


@app.route('/channel/<channel_uuid>/room/<room_uuid>/user/<user_uuid>/ban', methods=['PUT'])
def ban_user_room(channel_uuid: str, room_uuid: str, user_uuid: str):
    try:
        json_data = request.get_json()
        duration = json_data['duration']
    except Exception as e:
        logger.error('could not parse json: %s' % str(e))
        return jsonify({'status_code': 400, 'data': 'invalid json'})

    try:
        user_manager.ban_user(user_uuid, room_uuid, duration, 'room')
    except ValidationException as e:
        return jsonify({'status_code': 400, 'data': 'invalid duration: %s' % str(e)})
    except UnknownBanTypeException as e:
        return jsonify({'status_code': 500, 'data': 'could not ban user: %s' % str(e)})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status_code': 500, 'data': str(e)})
    return jsonify({'status_code': 200})


# TODO: currently no way in the cms to ban a user from a channel (or globally)
@app.route('/channel/<channel_uuid>/user/<user_uuid>/ban', methods=['PUT'])
def ban_user_channel(channel_uuid: str, user_uuid: str):
    try:
        json_data = request.get_json()
        duration = json_data['duration']
    except Exception as e:
        logger.error('could not parse json: %s' % str(e))
        return jsonify({'status_code': 400, 'data': 'invalid json'})

    try:
        user_manager.ban_user(user_uuid, channel_uuid, duration, 'channel')
    except ValidationException as e:
        return jsonify({'status_code': 400, 'data': 'invalid duration: %s' % str(e)})
    except UnknownBanTypeException as e:
        return jsonify({'status_code': 500, 'data': 'could not ban user: %s' % str(e)})
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status_code': 500, 'data': str(e)})
    return jsonify({'status_code': 200})


@app.route('/banned/room/<room_uuid>/user/<user_uuid>', methods=['DELETE'])
def remove_ban(room_uuid: str, user_uuid: str):
    user_manager.remove_ban(user_uuid, room_uuid, 'room')
    return jsonify({'status_code': 200})


@app.route('/banned', methods=['GET', 'POST'])
def banned():
    ban_form = BanForm(request.form)

    if request.method == 'POST' and ban_form.validate():
        try:
            user_manager.ban_user(
                    ban_form.uuid.data,
                    ban_form.target_id.data,
                    ban_form.duration.data,
                    ban_form.target_type.data)
            return redirect('/banned')
        except ValidationException as e:
            ban_form.target_type.errors.append('Ban not valid: "%s"' % e.msg)
        except UnknownBanTypeException as e:
            ban_form.target_type.errors.append('Unkonwn ban type "%s"' % e.ban_type)

    bans = user_manager.get_banned_users()
    return render_template(
            'banned.html',
            form=ban_form,
            globally=bans['global'],
            channels=bans['channels'],
            rooms=bans['rooms'])


@app.route('/users', methods=['GET'])
def users():
    form = CreateUserForm(request.form)
    return render_template(
            'users.html',
            form=form,
            superusers=user_manager.get_super_users())


@app.route('/user/<user_uuid>', methods=['GET'])
def user(user_uuid: str):
    return render_template('user.html', user=user_manager.get_user(user_uuid))


@app.route('/history', methods=['GET'])
def history():
    return render_template('history.html')


@app.route('/channel/<channel_uuid>/rooms', methods=['GET'])
def rooms_for_channel(channel_uuid):
    form = CreateRoomForm(request.form)
    acl_form = CreateChannelAclForm(request.form)
    owner_form = AddOwnerForm(request.form)
    admin_form = AddAdminForm(request.form)

    return render_template(
            'rooms_in_channel.html',
            form=form,
            owner_form=owner_form,
            admin_form=admin_form,
            acl_form=acl_form,
            owners=channel_manager.get_owners(channel_uuid),
            admins=channel_manager.get_admins(channel_uuid),
            acls=acl_manager.get_acls_channel(channel_uuid),
            channel_uuid=channel_uuid,
            channel_name=channel_manager.name_for_uuid(channel_uuid),
            rooms=room_manager.get_rooms(channel_uuid))


@app.route('/channel/<channel_uuid>/room/<room_uuid>', methods=['GET'])
def users_for_room(channel_uuid, room_uuid):
    owner_form = AddOwnerForm(request.form)
    mod_form = AddModeratorForm(request.form)
    acl_form = CreateRoomAclForm(request.form)

    return render_template(
            'users_in_room.html',
            channel_uuid=channel_uuid,
            room_uuid=room_uuid,
            owner_form=owner_form,
            mod_form=mod_form,
            acl_form=acl_form,
            acls=acl_manager.get_acls_room(room_uuid),
            channel_name=channel_manager.name_for_uuid(channel_uuid),
            room_name=room_manager.name_for_uuid(room_uuid),
            owners=room_manager.get_owners(room_uuid),
            moderators=room_manager.get_moderators(room_uuid),
            users=user_manager.get_users_for_room(room_uuid))


@app.route('/channel/<channel_uuid>/rename', methods=['PUT'])
def rename_channel(channel_uuid: str) -> None:
    try:
        json_data = request.get_json()
        new_name = json_data['name']
    except Exception as e:
        logger.error('could not parse json: %s' % str(e))
        return jsonify({'status_code': 400})

    try:
        channel_manager.rename(channel_uuid, new_name)
    except ChannelNameExistsException:
        return jsonify({'status_code': 400, 'message': 'A channel with that name already exists'})
    except EmptyChannelNameException:
        return jsonify({'status_code': 400, 'message': 'Blank channel name is not allowed'})

    return jsonify({'status_code': 200})


@app.route('/channel/<channel_uuid>/room/<room_uuid>/rename', methods=['PUT'])
def rename_room(channel_uuid: str, room_uuid: str) -> None:
    try:
        json_data = request.get_json()
        new_name = json_data['name']
    except Exception as e:
        logger.error('could not parse json: %s' % str(e))
        return jsonify({'status_code': 400})

    try:
        room_manager.rename(channel_uuid, room_uuid, new_name)
    except RoomNameExistsForChannelException:
        return jsonify({'status_code': 400, 'message': 'A room with that name already exists for this channel'})
    except EmptyRoomNameException:
        return jsonify({'status_code': 400, 'message': 'Blank room name is not allowed'})

    return jsonify({'status_code': 200})


@app.route('/channel/<channel_uuid>/room/<room_uuid>/acl/<action>/type/<acl_type>', methods=['DELETE'])
def delete_acl_room(channel_uuid, room_uuid, action, acl_type):
    acl_manager.delete_acl_room(room_uuid, action, acl_type)
    return jsonify({'status_code': 200})


@app.route('/channel/<channel_uuid>/room/<room_uuid>/acl/<action>/type/<acl_type>', methods=['PUT'])
def update_acl_room(channel_uuid, room_uuid, action, acl_type):
    try:
        json_data = request.get_json()
        new_value = json_data['value']
    except Exception as e:
        logger.error('could not parse json: %s' % str(e))
        return jsonify({'status_code': 400})

    try:
        acl_manager.update_room_acl(channel_uuid, room_uuid, action, acl_type, new_value)
    except InvalidAclValueException:
        return jsonify({'status_code': 400, 'message': 'Invalid ACL value'})
    except InvalidAclTypeException:
        return jsonify({'status_code': 400, 'message': 'Invalid ACL type'})
    except Exception as e:
        logger.error('could not update acl for room %s: %s' % (room_uuid, str(e)))
        print(traceback.format_exc())
        return jsonify({'status_code': 500, 'message': 'Could not update'})

    return jsonify({'status_code': 200})


@app.route('/channel/<channel_uuid>/acl/<action>/type/<acl_type>', methods=['PUT'])
def update_acl_channel(channel_uuid, action, acl_type):
    try:
        json_data = request.get_json()
        new_value = json_data['value']
    except Exception as e:
        logger.error('could not parse json: %s' % str(e))
        return jsonify({'status_code': 400})

    try:
        acl_manager.update_channel_acl(channel_uuid, action, acl_type, new_value)
    except InvalidAclValueException:
        return jsonify({'status_code': 400, 'message': 'Invalid ACL value'})
    except InvalidAclTypeException:
        return jsonify({'status_code': 400, 'message': 'Invalid ACL type'})
    except Exception as e:
        logger.error('could not update acl for channel %s: %s' % (channel_uuid, str(e)))
        print(traceback.format_exc())
        return jsonify({'status_code': 500, 'message': 'Could not update'})

    return jsonify({'status_code': 200})


@app.route('/channel/<channel_uuid>/acl/<action>/type/<acl_type>', methods=['DELETE'])
def delete_acl_channel(channel_uuid, action, acl_type):
    acl_manager.delete_acl_channel(channel_uuid, action, acl_type)
    return jsonify({'status_code': 200})


@app.route('/channel/<channel_uuid>/create', methods=['POST'])
def create_room(channel_uuid):
    form = CreateRoomForm(request.form)
    room_name = str(form.name.data)
    room_uuid = str(uuid())
    user_uuid = str(form.owner.data)

    if is_blank(room_name) or is_blank(user_uuid):
        return redirect('/channel/%s/rooms' % channel_uuid)

    room_manager.create_room(room_name, room_uuid, channel_uuid, user_uuid)
    return redirect('/channel/%s/room/%s' % (channel_uuid, room_uuid))


@app.route('/channel/<channel_uuid>/room/<room_uuid>/remove', methods=['DELETE'])
def delete_room(channel_uuid: str, room_uuid: str):
    room_manager.remove_room(channel_uuid, room_uuid)
    return jsonify({'status_code': 200})


@app.route('/channel/<channel_uuid>/create/acl', methods=['POST'])
def create_acl_channel(channel_uuid: str):
    form = CreateChannelAclForm(request.form)
    action = form.api_action.data
    acl_type = form.acl_type.data
    acl_value = form.acl_value.data

    if is_blank(acl_type) or is_blank(acl_value):
        return redirect('/channel/%s/rooms' % channel_uuid)

    # TODO: validate here

    acl_manager.add_acl_channel(channel_uuid, action, acl_type, acl_value)
    return redirect('/channel/%s/rooms' % channel_uuid)


@app.route('/channel/<channel_uuid>/add/admin', methods=['POST'])
def create_channel_admin(channel_uuid: str):
    form = AddAdminForm(request.form)
    user_id = form.uuid.data

    if is_blank(user_id):
        return redirect('/channel/%s/rooms' % channel_uuid)

    user_manager.add_channel_admin(channel_uuid, user_id)
    return redirect('/channel/%s/rooms' % channel_uuid)


@app.route('/channel/<channel_uuid>/add/owner', methods=['POST'])
def create_channel_owner(channel_uuid: str):
    form = AddOwnerForm(request.form)
    user_id = form.uuid.data

    if is_blank(user_id):
        return redirect('/channel/%s/rooms' % channel_uuid)

    user_manager.add_channel_owner(channel_uuid, user_id)
    return redirect('/channel/%s/rooms' % channel_uuid)


@app.route('/channel/<channel_uuid>/room/<room_uuid>/add/owner', methods=['POST'])
def create_room_owner(channel_uuid: str, room_uuid: str):
    form = AddOwnerForm(request.form)
    user_id = form.uuid.data

    if is_blank(user_id):
        return redirect('/channel/%s/room/%s' % (channel_uuid, room_uuid))

    user_manager.add_room_owner(room_uuid, user_id)
    return redirect('/channel/%s/room/%s' % (channel_uuid, room_uuid))


@app.route('/channel/<channel_uuid>/room/<room_uuid>/add/moderator', methods=['POST'])
def create_room_moderator(channel_uuid: str, room_uuid: str):
    form = AddModeratorForm(request.form)
    user_id = form.uuid.data

    if is_blank(user_id):
        return redirect('/channel/%s/room/%s' % (channel_uuid, room_uuid))

    user_manager.add_room_moderator(room_uuid, user_id)
    return redirect('/channel/%s/room/%s' % (channel_uuid, room_uuid))


@app.route('/channel/<channel_uuid>/remove/admin/<user_id>', methods=['DELETE'])
def remove_channel_admin(channel_uuid: str, user_id: str):
    if is_blank(user_id):
        return jsonify({'status_code': 200})

    user_manager.remove_channel_admin(channel_uuid, user_id)
    return jsonify({'status_code': 200})


@app.route('/channel/<channel_uuid>/remove/owner/<user_id>', methods=['DELETE'])
def remove_channel_owner(channel_uuid: str, user_id: str):
    if is_blank(user_id):
        return redirect('/channel/%s/rooms' % channel_uuid)

    user_manager.remove_channel_owner(channel_uuid, user_id)
    return jsonify({'status_code': 200})


@app.route('/channel/<channel_uuid>/room/<room_uuid>/remove/moderator/<user_id>', methods=['DELETE'])
def remove_room_moderator(channel_uuid: str, room_uuid: str, user_id: str):
    if is_blank(user_id):
        return jsonify({'status_code': 200})

    user_manager.remove_room_moderator(room_uuid, user_id)
    return jsonify({'status_code': 200})


@app.route('/channel/<channel_uuid>/room/<room_uuid>/remove/owner/<user_id>', methods=['DELETE'])
def remove_room_owner(channel_uuid: str, room_uuid: str, user_id: str):
    if is_blank(user_id):
        return jsonify({'status_code': 200})

    user_manager.remove_room_owner(room_uuid, user_id)
    return jsonify({'status_code': 200})


@app.route('/channel/<channel_uuid>/room/<room_uuid>/create/acl', methods=['POST'])
def create_acl_room(channel_uuid: str, room_uuid: str):
    form = CreateRoomAclForm(request.form)
    action = str(form.api_action.data).strip()
    acl_type = str(form.acl_type.data).strip()
    acl_value = str(form.acl_value.data).strip()

    if is_blank(acl_type) or is_blank(acl_value):
        return redirect('/channel/%s/room/%s' % (channel_uuid, room_uuid))

    # TODO: validate here

    acl_manager.add_acl_room(room_uuid, action, acl_type, acl_value)
    return redirect('/channel/%s/room/%s' % (channel_uuid, room_uuid))


@app.route('/create/channel', methods=['POST'])
def create_channel():
    form = CreateChannelForm(request.form)
    channel_name = str(form.name.data).strip()
    channel_uuid = str(uuid())
    user_uuid = str(form.owner.data).strip()

    if is_blank(channel_name) or is_blank(user_uuid):
        return redirect('/channels')

    channel_manager.create_channel(channel_name, channel_uuid, user_uuid)
    return redirect('/channel/%s/rooms' % channel_uuid)


@app.route('/create/super-user', methods=['POST'])
def create_admin_user():
    form = CreateUserForm(request.form)
    user_name = str(form.name.data).strip()
    user_id = str(form.uuid.data).strip()

    if is_blank(user_name) or is_blank(user_id):
        return redirect('/users')

    user_manager.create_admin_user(user_name, user_id)
    return redirect('/user/%s' % user_id)


@app.route('/static/custom/<path:path>')
def send_custom(path):
    return send_from_directory('admin/static/custom/', path)


@app.route('/images/<path:path>')
def send_images(path):
    return send_from_directory('admin/static/vendor/images/', path)


@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('admin/static/vendor/', path)


@app.route('/fonts/<path:path>')
def send_fonts(path):
    return send_from_directory('admin/static/vendor/fonts/', path)
