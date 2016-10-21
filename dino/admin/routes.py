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
from flask import request
from flask import send_from_directory
from flask import render_template
from flask import jsonify
import pkg_resources
import logging
from uuid import uuid4 as uuid

from dino.web import app
from dino.admin.orm import channel_manager
from dino.admin.orm import room_manager
from dino.admin.orm import user_manager

from dino.admin.forms import CreateChannelForm
from dino.admin.forms import CreateRoomForm


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


def is_blank(s: str):
    return s is None or len(s.strip()) == ''


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('home.html')


@app.route('/channels', methods=['GET'])
def channels():
    form = CreateChannelForm(request.form)
    return render_template(
            'channels.html',
            form=form,
            channels=channel_manager.get_channels())


@app.route('/users', methods=['GET'])
def users():
    return render_template('users.html')


@app.route('/history', methods=['GET'])
def history():
    return render_template('history.html')


@app.route('/channel/<channel_uuid>/rooms', methods=['GET'])
def rooms_for_channel(channel_uuid):
    form = CreateRoomForm(request.form)
    return render_template(
            'rooms_in_channel.html',
            form=form,
            owners=channel_manager.get_owners(channel_uuid),
            admins=channel_manager.get_admins(channel_uuid),
            channel_uuid=channel_uuid,
            channel_name=channel_manager.name_for_uuid(channel_uuid),
            rooms=room_manager.get_rooms(channel_uuid))


@app.route('/channel/<channel_uuid>/room/<room_uuid>', methods=['GET'])
def users_for_room(channel_uuid, room_uuid):
    return render_template(
            'users_in_room.html',
            channel_uuid=channel_uuid,
            room_uuid=room_uuid,
            channel_name=channel_manager.name_for_uuid(channel_uuid),
            room_name=room_manager.name_for_uuid(room_uuid),
            owners=room_manager.get_owners(room_uuid),
            moderators=room_manager.get_moderators(room_uuid),
            users=user_manager.get_users_for_room(room_uuid))


@app.route('/create/channel/<channel_uuid>/room', methods=['POST'])
def create_room(channel_uuid):
    form = CreateRoomForm(request.form)
    room_name = form.name.data
    room_uuid = str(uuid())
    user_uuid = form.owner.data
    user_name = form.username.data

    if is_blank(room_name) or is_blank(user_uuid) or is_blank(user_name):
        return redirect('/channel/%s/rooms' % channel_uuid)

    room_manager.create_room(room_name, room_uuid, channel_uuid, user_uuid, user_name)
    return redirect('/channel/%s/room/%s' % (channel_uuid, room_uuid))


@app.route('/create/channel', methods=['POST'])
def create_channel():
    form = CreateChannelForm(request.form)
    channel_name = form.name.data
    channel_uuid = str(uuid())
    user_uuid = form.owner.data

    if is_blank(channel_name) or is_blank(user_uuid):
        return redirect('/channels')

    channel_manager.create_channel(channel_name, channel_uuid, user_uuid)
    return redirect('/channel/%s/rooms' % channel_uuid)


@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('admin/static/', path)
