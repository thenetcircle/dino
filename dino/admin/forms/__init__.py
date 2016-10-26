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

from wtforms import Form, StringField, SelectField, validators

from dino.validation.acl_validator import AclValidator
from dino.config import SessionKeys

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


acl_choices = [
    (SessionKeys.age.value, 'Age'),
    (SessionKeys.gender.value, 'Gender'),
    (SessionKeys.membership.value, 'Membership'),
    (SessionKeys.group.value, 'Group'),
    (SessionKeys.country.value, 'Country'),
    (SessionKeys.city.value, 'City'),
    (SessionKeys.image.value, 'Image'),
    (SessionKeys.has_webcam.value, 'Has webcam'),
    (SessionKeys.fake_checked.value, 'Fake checked')
]


class CreateChannelForm(Form):
    name = StringField('Name', validators=[validators.DataRequired], description='Channel name')
    owner = StringField('Owner', validators=[validators.DataRequired], description='Owner ID')


class CreateRoomForm(Form):
    name = StringField('Name', validators=[validators.DataRequired], description='Room name')
    owner = StringField('Owner', validators=[validators.DataRequired], description='Owner ID')


class CreateUserForm(Form):
    name = StringField('Name', validators=[validators.DataRequired], description='Username')
    uuid = StringField('ID', validators=[validators.DataRequired], description='ID of the user')


class AddModeratorForm(Form):
    name = StringField('Name', validators=[validators.DataRequired], description='Username')
    uuid = StringField('ID', validators=[validators.DataRequired], description='ID of the user')


class AddOwnerForm(Form):
    name = StringField('Name', validators=[validators.DataRequired], description='Username')
    uuid = StringField('ID', validators=[validators.DataRequired], description='ID of the user')


class CreateAclForm(Form):
    acl_type = SelectField(
            'Type',
            choices=acl_choices,
            validators=[validators.DataRequired],
            description='Permission type')

    acl_value = StringField(
            'Value',
            validators=[validators.DataRequired],
            description='Permission value')
