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

from wtforms import Form, StringField, SelectField, TextAreaField, validators
from wtforms.validators import ValidationError

from dino.config import ApiTargets
from dino.config import ConfigKeys
from dino import environ
from dino.validation.duration import DurationValidator

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

acl_config = environ.env.config.get(ConfigKeys.ACL)
api_channel_actions = [(a, a.upper()) for a in acl_config[ApiTargets.CHANNEL].keys()]
api_room_actions = [(a, a.upper()) for a in acl_config[ApiTargets.ROOM].keys()]

channel_config = acl_config[ApiTargets.CHANNEL][api_channel_actions[0][0]]
channel_acls = set(channel_config['acls'])

if 'exclude' in channel_config:
    for exclude in channel_config['exclude']:
        channel_acls.remove(exclude)

room_config = acl_config[ApiTargets.ROOM][api_room_actions[0][0]]
room_acls = set(room_config['acls'])

if 'exclude' in room_config:
    for exclude in room_config['exclude']:
        room_acls.remove(exclude)

acl_channel_choices = [(a, a.capitalize()) for a in channel_acls]
acl_room_choices = [(a, a.capitalize()) for a in room_acls]


class CreateChannelForm(Form):
    name = StringField('Name', validators=[validators.DataRequired], description='Channel name')
    owner = StringField('Owner', validators=[validators.DataRequired], description='Owner ID')


class CreateRoomForm(Form):
    name = StringField('Name', validators=[validators.DataRequired], description='Room name')
    owner = StringField('Owner', validators=[validators.DataRequired], description='Owner ID')


class TargetRequiredIfNotGlobal(object):
    field_flags = ('required', )

    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        if form.target_type.data != 'global':
            if field.data is None or len(field.data.strip()) == 0:
                raise ValidationError('Need target ID if type is not global ban')


class NonBlankString(object):
    field_flags = ('required', )

    def __init__(self, value=None):
        self.value = value

    def __call__(self, form, field):
        if field.data is None or len(field.data.strip()) == 0:
            raise ValidationError('Need non-blank value')


class DurationRequired(object):
    field_flags = ('required', )

    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        try:
            DurationValidator(field.data)
        except Exception as e:
            raise ValidationError(str(e))


class BanForm(Form):
    uuid = StringField('ID', validators=[validators.DataRequired()], description='User ID')
    target_id = StringField('Target UUID', validators=[TargetRequiredIfNotGlobal()], description='Target UUID')
    duration = StringField('Duration', validators=[validators.DataRequired(), DurationRequired()])
    target_type = SelectField(
            'Type',
            choices=[('global', 'Global'), ('channel', 'Channel'), ('room', 'Room')],
            validators=[validators.DataRequired(), NonBlankString()])


class CreateUserForm(Form):
    name = StringField('Name', validators=[validators.DataRequired(), NonBlankString()], description='Username')
    uuid = StringField('ID', validators=[validators.DataRequired(), NonBlankString()], description='ID of the user')


class AddModeratorForm(Form):
    uuid = StringField('ID', validators=[validators.DataRequired(), NonBlankString()], description='ID of the user')


class AddOwnerForm(Form):
    uuid = StringField('ID', validators=[validators.DataRequired(), NonBlankString()], description='ID of the user')


class AddAdminForm(Form):
    uuid = StringField('ID', validators=[validators.DataRequired(), NonBlankString()], description='ID of the user')


class CreateChannelAclForm(Form):
    api_action = SelectField(
        'Action',
        choices=api_channel_actions,
        validators=[validators.DataRequired(), NonBlankString()],
        description='Permission type'
    )

    acl_type = SelectField(
        'Type',
        choices=acl_channel_choices,
        validators=[validators.DataRequired(), NonBlankString()],
        description='Permission type'
    )

    acl_value = StringField(
        'Value',
        validators=[validators.DataRequired(), NonBlankString()],
        description='Permission value'
    )


class SearchHistoryForm(Form):
    room_id = StringField('Room ID', description='Room ID')
    user_id = StringField('User ID', description='User ID')
    from_time = StringField('From timestamp', description='From timestamp')
    to_time = StringField('To timestamp', description='To timestamp')


class AddBlackListForm(Form):
    words = TextAreaField('Words', description='Words separated by new line')


class CreateRoomAclForm(Form):
    api_action = SelectField(
        'Action',
        choices=api_room_actions,
        validators=[validators.DataRequired(), NonBlankString()],
        description='Permission type'
    )

    acl_type = SelectField(
        'Type',
        choices=acl_room_choices,
        validators=[validators.DataRequired(), NonBlankString()],
        description='Permission type'
    )

    acl_value = StringField(
        'Value',
        validators=[validators.DataRequired(), NonBlankString()],
        description='Permission value'
    )
