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
import sys
import traceback
from datetime import datetime
from datetime import timedelta
from functools import wraps
from typing import List
from typing import Union, Optional
from typing import Dict
from uuid import uuid4 as uuid

import pytz
from activitystreams import Activity
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.orm.exc import UnmappedInstanceError
from sqlalchemy.exc import IntegrityError
from zope.interface import implementer

from dino.config import ApiActions, SessionKeys
from dino.config import ApiTargets
from dino.config import ConfigKeys
from dino.config import RoleKeys
from dino.config import UserKeys
from dino.db import IDatabase
from dino.db.rdbms.dbman import Database
from dino.db.rdbms.mock import MockDatabase
from dino.db.rdbms.models import AclConfigs, UserInfo, Joins
from dino.db.rdbms.models import Spams
from dino.db.rdbms.models import Config
from dino.db.rdbms.models import Acls
from dino.db.rdbms.models import Bans
from dino.db.rdbms.models import BlackList
from dino.db.rdbms.models import ChannelRoles
from dino.db.rdbms.models import Channels
from dino.db.rdbms.models import DefaultRooms
from dino.db.rdbms.models import GlobalRoles
from dino.db.rdbms.models import LastReads
from dino.db.rdbms.models import LastOnline
from dino.db.rdbms.models import RoomRoles
from dino.db.rdbms.models import RoomSids
from dino.db.rdbms.models import Rooms
from dino.db.rdbms.models import Sids
from dino.db.rdbms.models import UserStatus
from dino.db.rdbms.models import Users
from dino.environ import GNEnvironment
from dino.exceptions import AclValueNotFoundException
from dino.exceptions import ChannelExistsException
from dino.exceptions import ChannelNameExistsException
from dino.exceptions import EmptyChannelNameException
from dino.exceptions import EmptyRoomNameException
from dino.exceptions import EmptyUserIdException
from dino.exceptions import EmptyUserNameException
from dino.exceptions import InvalidAclTypeException
from dino.exceptions import InvalidAclValueException
from dino.exceptions import InvalidApiActionException
from dino.exceptions import NoChannelFoundException
from dino.exceptions import NoSuchChannelException
from dino.exceptions import NoSuchRoomException
from dino.exceptions import NoSuchUserException
from dino.exceptions import RoomExistsException
from dino.exceptions import RoomNameExistsForChannelException
from dino.exceptions import MultipleRoomsFoundForNameException
from dino.exceptions import UserExistsException
from dino.exceptions import ValidationException
from dino.utils import b64d
from dino.utils import b64e
from dino.utils import is_base64

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


def with_session(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        session = DatabaseRdbms.db.Session()
        try:
            kwargs['session'] = session
            return view_func(*args, **kwargs)
        except:
            session.rollback()
            raise
        finally:
            DatabaseRdbms.db.Session.remove()
    return wrapped


@implementer(IDatabase)
class DatabaseRdbms(object):
    def __init__(self, env: GNEnvironment):
        self.env = env
        if self.env.config.get(ConfigKeys.TESTING, False):
            DatabaseRdbms.db = MockDatabase()
        else:
            DatabaseRdbms.db = Database(env)

        self.count_cumulative_joins = env.config.get(
            ConfigKeys.COUNT_CUMULATIVE_JOINS, default=False
        )

    @with_session
    def _session(self, session):
        return session

    @with_session
    def init_config(self, session=None):
        config = session.query(Config).first()
        if config is not None:
            return

        config = Config()
        session.add(config)
        session.commit()

    @with_session
    def get_service_config(self, session=None) -> dict:
        config = session.query(Config).first()
        return {
            'spam_enabled': config.spam_enabled,
            'spam_min_length': config.spam_min_length,
            'spam_max_length': config.spam_max_length,
            'spam_threshold': config.spam_threshold,
            'spam_ignore_emoji': config.spam_ignore_emoji,
            'spam_should_delete': config.spam_should_delete,
            'spam_should_save': config.spam_should_save
        }

    def get_all_permanent_rooms(self):
        @with_session
        def _get_all_permanent_rooms(session=None):
            rooms = session.query(Rooms).filter(Rooms.ephemeral.is_(False)).all()
            if rooms is None or len(rooms) == 0:
                return dict()

            room_acls = dict()
            for room in rooms:
                acls = self.get_all_acls_room(room.uuid)
                room_acls[room.uuid] = acls

            return room_acls

        all_rooms = self.env.cache.get_all_permanent_rooms()
        if all_rooms is not None:
            return all_rooms

        all_rooms = _get_all_permanent_rooms()
        self.env.cache.set_all_permanent_rooms(all_rooms)

        return all_rooms

    def is_room_ephemeral(self, room_id: str) -> bool:
        @with_session
        def is_ephemeral(session=None):
            room = session.query(Rooms).filter(Rooms.uuid == room_id).first()
            if room is None:
                raise NoSuchRoomException(room_id)
            return room.ephemeral

        value = self.env.cache.is_room_ephemeral(room_id)
        if value is not None:
            return value
        value = is_ephemeral()
        self.env.cache.set_is_room_ephemeral(room_id, value)
        return value

    def get_black_list(self) -> set:
        @with_session
        def _get_black_list(session=None):
            rows = session.query(BlackList).all()
            return {row.word.lower().strip() for row in rows}

        blacklist = self.env.cache.get_black_list()
        if blacklist is not None:
            return blacklist

        blacklist = _get_black_list()
        if len(blacklist) > 0:
            self.env.cache.set_black_list(blacklist)
        return blacklist

    def remove_matching_word_from_blacklist(self, word: str) -> None:
        @with_session
        def _delete(_word: str, session=None) -> None:
            session.query(BlackList).filter(func.lower(BlackList.word) == func.lower(_word))\
                .delete(synchronize_session='fetch')
            session.commit()

        if word is None or len(word.strip()) == 0:
            raise ValueError('empty word when deleting from word list')
        _delete(word)
        self.env.cache.reset_black_list()

    def remove_word_from_blacklist(self, word_id) -> None:
        @with_session
        def _delete(_id: int, session=None) -> None:
            session.query(BlackList).filter(BlackList.id == _id).delete()
            session.commit()

        if word_id is None or len(word_id.strip()) == 0:
            raise ValueError('empty id when deleting from word list')
        try:
            word_id = int(word_id)
        except ValueError:
            logger.error('invalid id for word: "%s"' % word_id)
            raise
        _delete(word_id)
        self.env.cache.reset_black_list()

    @with_session
    def add_words_to_blacklist(self, words: list, session=None) -> None:
        all_words = {row.word.lower() for row in session.query(BlackList).all()}
        for word in words:
            if word is None or len(word.strip()) == 0 or word.strip().lower() in all_words:
                continue
            blacklisted = BlackList()
            blacklisted.word = word
            session.add(blacklisted)
        session.commit()
        self.env.cache.reset_black_list()

    @with_session
    def get_black_list_with_ids(self, session=None) -> list:
        rows = session.query(BlackList).all()
        return [{'id': row.id, 'word': row.word} for row in rows]

    def _update_user_roles_in_cache(self, user_id: str) -> None:
        self.env.cache.reset_user_roles(user_id)
        self.get_user_roles(user_id, skip_cache=True)

    @with_session
    def increase_join_count(self, room_id: str, room_name: str, session=None) -> None:
        join = session.query(Joins).filter(Joins.room_id == room_id).first()
        if join is None:
            join = Joins(
                amount=0,
                room_id=room_id,
                room_name=room_name
            )

        join.amount += 1
        self.env.cache.set_join_count(room_id, join.amount)
        self.env.cache.set_join_count_by_name(room_name, join.amount)

        session.add(join)
        session.commit()

    def get_joins_in_room_by_name(self, room_name: str) -> int:
        @with_session
        def _get_joins(session=None) -> int:
            join = session.query(Joins).filter(Joins.room_name == room_name).first()
            if join is None:
                # can't create it since we only know the name not the id here
                logger.warning("can't count joins for unknown room name '{}', returning 0".format(room_name))
                return 0

            return join.amount

        n_joins = self.env.cache.get_join_count_by_name(room_name)
        if n_joins is not None:
            return n_joins

        n_joins = _get_joins()
        self.env.cache.set_join_count_by_name(room_name, n_joins)

        return n_joins

    def get_joins_in_room(self, room_id: str) -> int:
        @with_session
        def _get_joins(session=None) -> int:
            join = session.query(Joins).filter(Joins.room_id == room_id).first()
            if join is None:
                # can't create it since we only know the id not the name here
                logger.warning("can't count joins for unknown room name '{}', returning 0".format(room_id))
                return 0

            return join.amount

        n_joins = self.env.cache.get_join_count(room_id)
        if n_joins is not None:
            return n_joins

        n_joins = _get_joins()
        self.env.cache.set_join_count(room_id, n_joins)

        return n_joins

    def get_user_roles_in_room(self, user_id: str, room_id: str) -> list:
        @with_session
        def _room_roles(session=None) -> list:
            _roles = session.query(RoomRoles)\
                .join(RoomRoles.room)\
                .filter(RoomRoles.user_id == user_id)\
                .filter(Rooms.uuid == room_id)\
                .first()

            if _roles is None or _roles.roles is None:
                return list()
            return [a for a in _roles.roles.split(',') if len(a) > 0]

        @with_session
        def _global_roles(session=None) -> list:
            _roles = session.query(GlobalRoles)\
                .filter(GlobalRoles.user_id == user_id)\
                .first()

            if _roles is None or _roles.roles is None:
                return list()
            return [a for a in _roles.roles.split(',') if len(a) > 0]

        output = self.env.cache.get_user_roles(user_id)

        if output is not None and room_id in output['room']:
            room_roles = output['room'][room_id]
        else:
            room_roles = _room_roles()

        if output is not None and room_id in output['global']:
            global_roles = output['global']
        else:
            global_roles = _global_roles()

        return room_roles + global_roles

    def get_admins_in_room(self, room_id: str, this_user_id: str=None) -> set:
        users = self.users_in_room(room_id, this_user_id, skip_cache=True)
        mods_in_room = list()
        for user_id, _ in users.items():
            if not self.is_super_user(user_id) and not self.is_global_moderator(user_id):
                continue
            mods_in_room.append(user_id)
        return set(mods_in_room)

    @with_session
    def get_online_admins(self, session=None) -> list:
        admins = session.query(GlobalRoles).filter(or_(
                GlobalRoles.roles.ilike('%{}%'.format(RoleKeys.SUPER_USER)),
                GlobalRoles.roles.ilike('%{}%'.format(RoleKeys.GLOBAL_MODERATOR))
        )).all()
        admin_ids = [admin.user_id for admin in admins]
        if len(admin_ids) == 0:
            return []

        online_admins = session.query(UserStatus)\
            .filter(UserStatus.status.in_([
                UserKeys.STATUS_INVISIBLE,
                UserKeys.STATUS_AVAILABLE,
                UserKeys.STATUS_CHAT]))\
            .filter(UserStatus.uuid.in_(admin_ids)).all()
        return [admin.uuid for admin in online_admins]

    @with_session
    def get_users_roles(self, user_ids: list, session=None) -> None:
        g_roles = session.query(GlobalRoles).all()
        c_roles = session.query(ChannelRoles).join(ChannelRoles.channel).all()
        r_roles = session.query(RoomRoles).join(RoomRoles.room).all()

        user_g_roles = {g.user_id: g for g in g_roles}
        user_c_roles = dict()
        user_r_roles = dict()

        for c_role in c_roles:
            if c_role.user_id not in user_c_roles:
                user_c_roles[c_role.user_id] = list()
            user_c_roles[c_role.user_id].append(c_role)

        for r_role in r_roles:
            if r_role.user_id not in user_r_roles:
                user_r_roles[r_role.user_id] = list()
            user_r_roles[r_role.user_id].append(r_role)

        for user_id in user_ids:
            roles = self._format_user_roles(
                user_g_roles.get(user_id), user_c_roles.get(user_id), user_r_roles.get(user_id))
            self.env.cache.set_user_roles(user_id, roles)

    def _format_user_roles(self, g_roles, c_roles, r_roles) -> dict:
        _output = {
            'global': list(),
            'channel': dict(),
            'room': dict()
        }

        if g_roles is not None:
            _output['global'] = [a for a in g_roles.roles.split(',') if len(a) > 0]

        if c_roles is not None and len(c_roles) > 0:
            for c_role in c_roles:
                _output['channel'][c_role.channel.uuid] = [a for a in c_role.roles.split(',') if len(a) > 0]
        if r_roles is not None and len(r_roles) > 0:
            for r_role in r_roles:
                _output['room'][r_role.room.uuid] = [a for a in r_role.roles.split(',') if len(a) > 0]
        return _output

    def get_room_owners(self, room_id: str):
        @with_session
        def _get_owners(session=None) -> List[str]:
            return session.query(RoomRoles.user_id) \
                .join(RoomRoles.room) \
                .filter(Rooms.uuid == room_id) \
                .filter(RoomRoles.roles.contains(RoleKeys.OWNER)) \
                .all()

        owners = self.env.cache.get_room_owners(room_id)
        if owners is not None:
            return owners

        owners = {owner[0] for owner in _get_owners()}
        logger.info("owners of room {}: {}".format(room_id, owners))

        self.env.cache.set_room_owners(room_id, owners)

        return owners

    def get_user_roles(self, user_id: str, skip_cache: bool = False) -> dict:
        @with_session
        def _roles(session=None) -> dict:
            g_roles, c_roles, r_roles = (
                session.query(GlobalRoles).filter(GlobalRoles.user_id == user_id).first(),
                session.query(ChannelRoles).join(ChannelRoles.channel).filter(ChannelRoles.user_id == user_id).all(),
                session.query(RoomRoles).join(RoomRoles.room).filter(RoomRoles.user_id == user_id).all()
            )
            return self._format_user_roles(g_roles, c_roles, r_roles)

        if not skip_cache:
            output = self.env.cache.get_user_roles(user_id)

            if output is not None:
                did_reset_user_roles = False
                if 'room' in output:
                    for room_id in output['room']:
                        try:
                            self.get_room_name(room_id)
                        except NoSuchRoomException:
                            logger.warning(
                                'user has room %s in roles, but room does not exist; will delete role' % room_id)
                            self.env.cache.reset_user_roles(user_id)
                            did_reset_user_roles = True
                            break
                if not did_reset_user_roles:
                    return output

        roles = _roles()
        self.env.cache.set_user_roles(user_id, roles)
        return roles

    @with_session
    def set_admin_room(self, room_uuid: str, session=None) -> None:
        room = session.query(Rooms).filter(Rooms.uuid == room_uuid).first()
        if room is None:
            return

        room.admin = True

        has_join_acl = False
        has_list_acl = False

        for acl in room.acls:
            if acl.acl_type != RoleKeys.ADMIN:
                continue
            if acl.action == ApiActions.JOIN:
                has_join_acl = True
            elif acl.action == ApiActions.LIST:
                has_list_acl = True

        if not has_list_acl:
            list_acl = Acls()
            list_acl.action = ApiActions.LIST
            list_acl.acl_type = RoleKeys.ADMIN
            list_acl.acl_value = ''
            session.add(list_acl)
            room.acls.append(list_acl)
        if not has_join_acl:
            join_acl = Acls()
            join_acl.action = ApiActions.JOIN
            join_acl.acl_type = RoleKeys.ADMIN
            join_acl.acl_value = ''
            session.add(join_acl)
            room.acls.append(join_acl)

        self.env.cache.set_admin_room(room_uuid)
        session.commit()

    @with_session
    def unset_admin_room(self, room_uuid: str, session=None) -> None:
        room = session.query(Rooms).filter(Rooms.uuid == room_uuid).first()
        if room is None:
            return

        room.admin = False
        self.env.cache.remove_admin_room()
        session.commit()

    def create_admin_room(self) -> str:
        @with_session
        def _create(admin_channel_id: str, session=None):
            # only need to set admin, super users will be able to join as well, since they bypass acl validation anyway
            join_acl = Acls()
            join_acl.action = ApiActions.JOIN
            join_acl.acl_type = RoleKeys.ADMIN
            join_acl.acl_value = ''
            session.add(join_acl)

            list_acl = Acls()
            list_acl.action = ApiActions.LIST
            list_acl.acl_type = RoleKeys.ADMIN
            list_acl.acl_value = ''
            session.add(list_acl)

            channel = session.query(Channels).filter(Channels.uuid == admin_channel_id).first()

            room = Rooms()
            room.name = 'Admins'
            room.created = datetime.utcnow()
            room.admin = True
            room.uuid = str(uuid())
            room.channel = channel
            room.ephemeral = False
            room.acls.append(join_acl)
            room.acls.append(list_acl)

            session.add(room)
            session.commit()
            return room.uuid

        try:
            self.create_user('0', 'Admin')
            self.set_super_user('0')
        except UserExistsException:
            pass

        admin_room_id = self.get_admin_room()
        if admin_room_id is not None:
            return admin_room_id

        channel_id = str(uuid())
        self.create_channel('Admins', channel_id, '0')
        return _create(channel_id)

    @with_session
    def get_admin_room(self, session=None) -> str:
        room = session.query(Rooms)\
            .filter(Rooms.admin.is_(True))\
            .first()
        if room is None:
            return None
        return room.uuid

    def room_exists(self, channel_id: str, room_id: str) -> bool:
        @with_session
        def _room_exists(session=None):
            rooms = session.query(Rooms) \
                .filter(Rooms.uuid == room_id) \
                .all()

            exists = len(rooms) > 0
            if exists:
                self.env.cache.set_room_exists(channel_id, room_id, rooms[0].name)
            return exists

        exists = self.env.cache.get_room_exists(channel_id, room_id)
        if exists is not None:
            return exists
        return _room_exists()

    def get_user_status(self, user_id: str, skip_cache: bool = False) -> str:
        @with_session
        def _get_user_status(session=None):
            status = session.query(UserStatus).filter_by(uuid=user_id).first()
            if status is None:
                return UserKeys.STATUS_UNAVAILABLE
            return status.status

        if not skip_cache:
            status = self.env.cache.get_user_status(user_id)
            if status is not None:
                return status

        status = _get_user_status()
        self.env.cache.set_user_status(user_id, status)
        return status

    def set_user_invisible(self, user_id: str, is_offline=False) -> None:
        @with_session
        def _set_user_invisible(session=None):
            user_status = session.query(UserStatus).filter(UserStatus.uuid == user_id).first()
            if user_status is None:
                user_status = UserStatus()
                user_status.uuid = user_id

            user_status.status = UserKeys.STATUS_INVISIBLE
            session.add(user_status)
            session.commit()

        if is_offline:
            self.env.cache.set_user_status_invisible(user_id)
        else:
            self._set_last_online(user_id)
            self.env.cache.set_user_invisible(user_id)

        try:
            _set_user_invisible()
        except (IntegrityError, StaleDataError) as e:
            logger.warning('could not set user %s invisible, will try again: %s' % (user_id, str(e)))
            try:
                _set_user_invisible()
            except (IntegrityError, StaleDataError) as e:
                logger.error('could not set user %s invisible second time, logging to sentry: %s' % (user_id, str(e)))
                self.env.capture_exception(sys.exc_info())
            except Exception as e:
                logger.error('other error when trying to set user %s invisible second try: %s' % (user_id, str(e)))
                logger.exception(traceback.format_exc())
                self.env.capture_exception(sys.exc_info())

    @with_session
    def get_last_online_since(self, days: int, session=None) -> list:
        if days > 0:
            u = datetime.utcnow()
            u = u.replace(tzinfo=pytz.utc)
            u = u - timedelta(days=days)
            unix_time = int(u.timestamp())

            lasts = session.query(LastOnline).filter(LastOnline.at > unix_time).all()
        else:
            lasts = session.query(LastOnline).all()

        if lasts is None:
            return list()

        return [(last.uuid, last.at) for last in lasts]

    @with_session
    def _set_last_online(self, user_id: str, session=None):
        u = datetime.utcnow()
        u = u.replace(tzinfo=pytz.utc)
        unix_time = int(u.timestamp())

        last_online = session.query(LastOnline).filter(LastOnline.uuid == user_id).first()
        if last_online is None:
            last_online = LastOnline()
            last_online.uuid = user_id

        last_online.at = unix_time
        session.add(last_online)
        session.commit()

    def set_user_offline(self, user_id: str) -> None:
        @with_session
        def _set_user_offline(session=None):
            status = session.query(UserStatus).filter(UserStatus.uuid == user_id).first()
            if status is None:
                logger.warning('no UserStatus found in db for user ID %s' % user_id)
                return
            session.delete(status)
            session.commit()

        logger.debug('setting user %s as offline in cache' % user_id)
        self.env.cache.set_user_offline(user_id)

        try:
            self._set_last_online(user_id)
        except Exception as e:
            logger.error('could not set last_online in db for user {}: {}'.format(user_id, str(e)))
            logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())

        try:
            _set_user_offline()
        except (IntegrityError, StaleDataError) as e:
            logger.warning('could not set user %s offline, will try again: %s' % (user_id, str(e)))
            try:
                _set_user_offline()
            except (IntegrityError, StaleDataError) as e:
                logger.error('could not set user %s offline second time, logging to sentry: %s' % (user_id, str(e)))
                self.env.capture_exception(sys.exc_info())
            except Exception as e:
                logger.error('other error when trying to set user %s offline second try: %s' % (user_id, str(e)))
                logger.exception(traceback.format_exc())
                self.env.capture_exception(sys.exc_info())

    def set_user_online(self, user_id: str) -> None:
        @with_session
        def _set_user_online(session=None):
            user_status = session.query(UserStatus).filter(UserStatus.uuid == user_id).first()
            if user_status is None:
                user_status = UserStatus()
                user_status.uuid = user_id
                session.add(user_status)

            user_status.status = UserKeys.STATUS_AVAILABLE
            session.commit()

        self.env.cache.set_user_online(user_id)

        try:
            _set_user_online()
        except (IntegrityError, StaleDataError) as e:
            logger.warning('could not set user %s online, will try again: %s' % (user_id, str(e)))
            try:
                _set_user_online()
            except (IntegrityError, StaleDataError) as e:
                logger.error('could not set user %s online second time, logging to sentry: %s' % (user_id, str(e)))
                self.env.capture_exception(sys.exc_info())
            except Exception as e:
                logger.error('other error when trying to set user %s online second try: %s' % (user_id, str(e)))
                logger.exception(traceback.format_exc())
                self.env.capture_exception(sys.exc_info())

    def rooms_for_user(self, user_id: str, skip_cache: bool = False) -> dict:
        @with_session
        def _rooms_for_user(session=None) -> dict:
            rows = session.query(Rooms)\
                .join(Rooms.users)\
                .filter(Users.uuid == user_id)\
                .all()

            clean_rooms = dict()
            for row in rows:
                clean_rooms[row.uuid] = row.name
            return clean_rooms

        if skip_cache:
            rooms = _rooms_for_user()
            self.env.cache.set_rooms_for_user(user_id, rooms)
            return rooms

        rooms = self.env.cache.get_rooms_for_user(user_id)
        if rooms is not None and len(rooms) > 0:
            return rooms

        rooms = _rooms_for_user()
        self.env.cache.set_rooms_for_user(user_id, rooms)
        return rooms

    def type_of_rooms_in_channel(self, channel_id: str) -> str:
        object_type = self.env.cache.get_type_of_rooms_in_channel(channel_id)
        if object_type is not None:
            return object_type

        rooms = self.rooms_for_channel(channel_id)
        ephemeral = 0
        static = 0
        for _, room in rooms.items():
            if room['ephemeral']:
                ephemeral += 1
            else:
                static += 1

        if ephemeral >= 0 and static == 0:
            object_type = 'temporary'
        elif ephemeral == 0 and static > 0:
            object_type = 'static'
        else:
            object_type = 'mix'

        self.env.cache.set_type_of_rooms_in_channel(channel_id, object_type)
        return object_type

    def get_all_rooms(self) -> list:
        @with_session
        def _all_rooms(session=None):
            all_rooms = session.query(Rooms)\
                .join(Rooms.channel)\
                .all()

            return [
                {
                    'id': room.uuid,
                    'status': 'temporary' if room.ephemeral else 'static',
                    'name': room.name,
                    'channel': room.channel.name,
                    'channel_id': room.channel.uuid,
                } for room in all_rooms
            ]

        rooms = self.env.cache.get_all_rooms()
        if rooms is not None:
            return rooms

        try:
            rooms = _all_rooms()
        except Exception as e:
            logger.error('could not get rooms: {}'.format(str(e)))
            logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            return list()

        self.env.cache.set_all_rooms(rooms)
        return rooms

    def rooms_for_channel_without_info(self, channel_id: str) -> dict:
        @with_session
        def _rooms_for_channel(session=None):
            all_rooms = session.query(Rooms)\
                .join(Rooms.channel)\
                .filter(Channels.uuid == channel_id)\
                .all()

            return {
                room.uuid: {
                    'ephemeral': room.ephemeral,
                    'name': room.name
                } for room in all_rooms
            }

        channels = self.env.cache.get_rooms_for_channel(channel_id, with_info=False)
        if channels is not None:
            return channels

        try:
            channels = _rooms_for_channel()
        except Exception as e:
            logger.error('could not get rooms: {}'.format(str(e)))
            logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())
            return dict()

        self.env.cache.set_rooms_for_channel(channel_id, channels, with_info=False)
        return channels

    def rooms_for_channel(self, channel_id) -> dict:
        def _rooms():
            @with_session
            def _user_ids_and_room_data(session=None):
                all_rooms = session.query(Rooms)\
                    .join(Rooms.channel)\
                    .outerjoin(Rooms.users)\
                    .filter(Channels.uuid == channel_id)\
                    .all()

                unique_users = set()
                room_info = dict()
                for room in all_rooms:
                    room_info[room.uuid] = dict()
                    room_info[room.uuid]['name'] = room.name
                    room_info[room.uuid]['sort_order'] = room.sort_order
                    room_info[room.uuid]['ephemeral'] = room.ephemeral
                    room_info[room.uuid]['admin'] = room.admin
                    room_info[room.uuid]['users'] = [user.uuid for user in room.users]
                    for user in room.users:
                        unique_users.add(user.uuid)
                return unique_users, room_info

            def _user_statuses(_user_ids: set):
                user_statuses = dict()
                for user_id in _user_ids:
                    user_statuses[user_id] = self.get_user_status(user_id)
                return user_statuses

            def _get_the_rooms(all_rooms: dict, user_statuses: dict):
                rooms_with_n_users = dict()
                for room_id in all_rooms.keys():
                    visible_users = set()

                    for user_id in all_rooms[room_id]['users']:
                        if user_id in user_statuses and user_statuses[user_id] == UserKeys.STATUS_INVISIBLE:
                            continue
                        visible_users.add(user_id)

                    rooms_with_n_users[room_id] = {
                        'name': all_rooms[room_id]['name'],
                        'sort_order': all_rooms[room_id]['sort_order'],
                        'ephemeral': all_rooms[room_id]['ephemeral'],
                        'admin': all_rooms[room_id]['admin'],
                        'users': len(visible_users)
                    }
                return rooms_with_n_users

            # avoid overwriting the session variable
            user_ids, room_data = _user_ids_and_room_data()
            return _get_the_rooms(room_data, _user_statuses(user_ids))

        rooms = self.env.cache.get_rooms_for_channel(channel_id)
        if rooms is None:
            rooms = _rooms()
            self.env.cache.set_rooms_for_channel(channel_id, rooms)
        return rooms

    @with_session
    def search_for_users(self, query: str, session=None) -> list:
        users = session.query(Users) \
            .filter(or_(
                Users.uuid.ilike('%{}%'.format(query)),
                Users.name.ilike('%{}%'.format(query))
            ))\
            .limit(101)\
            .all()
        output = list()
        for user in users:
            output.append({
                'uuid': user.uuid,
                'name': user.name
            })
        return output

    def users_in_room(
            self, room_id: str = None, this_user_id: str = None, skip_cache: bool = False, room_name: str = None
    ) -> dict:
        @with_session
        def _user_ids(session=None):
            if room_id is not None:
                room = session.query(Rooms).outerjoin(Rooms.users).filter(Rooms.uuid == room_id).first()
            else:
                room = session.query(Rooms).outerjoin(Rooms.users).filter(Rooms.name == room_name).first()

            users_in_room = dict()

            if room is None:
                logger.warning('no room found for UUID/name "{}"/"{}"'.format(room_id, room_name))
                return users_in_room

            for user in room.users:
                users_in_room[user.uuid] = user.name

            return users_in_room

        def _user_statuses(user_ids: dict):
            statuses = dict()
            for user_id in user_ids.keys():
                statuses[user_id] = self.get_user_status(user_id)
            return statuses

        def _visible_users(every_user_in_room: dict, statuses: dict) -> dict:
            visible_users = dict()
            for user_id, user_name in every_user_in_room.items():
                if not is_super_user \
                        and user_id in statuses \
                        and statuses[user_id] == UserKeys.STATUS_INVISIBLE:
                    continue
                visible_users[user_id] = user_name
            return visible_users

        is_super_user = False
        if this_user_id is not None:
            is_super_user = self.is_super_user(this_user_id) or self.is_global_moderator(this_user_id)

        if not skip_cache:
            if room_id is None:
                users = self.env.cache.get_users_in_room_by_name(room_name, is_super_user=is_super_user)
            else:
                users = self.env.cache.get_users_in_room(room_id, is_super_user=is_super_user)

            if users is not None:
                return users.copy()

        all_users = _user_ids()
        user_statuses = _user_statuses(all_users)
        users = _visible_users(all_users, user_statuses)

        if room_id is None:
            self.env.cache.set_users_in_room_by_name(room_name, users, is_super_user=is_super_user)
        else:
            self.env.cache.set_users_in_room(room_id, users, is_super_user=is_super_user)

        return users

    def room_contains(self, room_id: str, user_id: str) -> bool:
        self.get_room_name(room_id)
        self.channel_for_room(room_id)
        return room_id in self.rooms_for_user(user_id)

    def remove_current_rooms_for_user(self, user_id):
        @with_session
        def remove(room_sids: dict, session=None) -> None:

            for i in range(3):
                try:
                    self._remove_current_rooms_for_user(user_id, room_sids, session)
                    return
                except StaleDataError as e:
                    logger.warning('stale data when removing current rooms for user, attempt {}/2: {}'.format(
                        str(i), str(e)
                    ))
            logger.error('got stale data after 3 retries, giving up')

        sids_to_rooms = self.get_rooms_with_sid(user_id)
        room_to_sids = dict()
        for sid, room in sids_to_rooms.items():
            if room not in room_to_sids:
                room_to_sids[room] = set()
            room_to_sids[room].add(sid)

        remove(room_to_sids)

    def set_ephemeral_room(self, room_id: str):
        self._set_ephemeral_on_room_to(room_id, is_ephemeral=True)

    def unset_ephemeral_room(self, room_id: str):
        self._set_ephemeral_on_room_to(room_id, is_ephemeral=False)

    @with_session
    def get_rooms_with_sid(self, user_id: str, session=None):
        room_sids = session.query(RoomSids).filter_by(user_id=user_id).all()
        return {rs.session_id: rs.room_id for rs in room_sids}

    def remove_sid_for_user_in_room(self, user_id, room_id, sid_to_remove):
        @with_session
        def _remove_sid_for_user_in_room(session=None):
            if room_id is None:
                sids = session.query(RoomSids) \
                    .filter_by(user_id=user_id) \
                    .all()
            else:
                sids = session.query(RoomSids) \
                    .filter_by(room_id=room_id) \
                    .filter_by(user_id=user_id) \
                    .all()

            for sid in sids:
                if sid_to_remove is None or sid_to_remove == sid.session_id:
                    session.delete(sid)
            session.commit()

        for _ in range(3):
            try:
                _remove_sid_for_user_in_room()
                break
            except Exception as e:
                logger.error('could not remove sid {} for user {} in room {}: {}'.format(
                    sid_to_remove, user_id, room_id, str(e)
                ))

        self.env.cache.remove_sid_for_user(user_id, sid_to_remove)

    @with_session
    def sids_for_user_in_room(self, user_id, room_id, session=None) -> set:
        sids = session.query(RoomSids) \
            .filter_by(room_id=room_id) \
            .filter_by(user_id=user_id) \
            .all()
        return {sid.session_id for sid in sids}

    @with_session
    def _set_ephemeral_on_room_to(self, room_id: str, is_ephemeral: bool, session=None):
        room = session.query(Rooms).filter(Rooms.uuid == room_id).first()
        if room is None:
            return
        room.ephemeral = is_ephemeral
        session.commit()
        channel_id = self.channel_for_room(room_id)
        self.env.cache.reset_rooms_for_channel(channel_id)

    def add_default_room(self, room_id: str) -> None:
        @with_session
        def _add_default_room(session=None):
            room = session.query(DefaultRooms).filter(DefaultRooms.uuid == room_id).first()
            if room is not None:
                return
            default_room = DefaultRooms()
            default_room.uuid = room_id
            session.add(default_room)
            session.commit()

        _add_default_room()
        self.env.cache.clear_default_rooms()
        self.get_default_rooms()

    def remove_default_room(self, room_id: str) -> None:
        @with_session
        def _remove_default_room(session=None):
            room = session.query(DefaultRooms).filter(DefaultRooms.uuid == room_id).first()
            if room is None:
                return
            session.delete(room)
            session.commit()

        _remove_default_room()
        self.env.cache.clear_default_rooms()
        self.get_default_rooms()

    def get_default_rooms(self) -> list:
        @with_session
        def _get_default_rooms(session=None) -> list:
            rooms = session.query(DefaultRooms).all()
            return [room.uuid for room in rooms]

        default_rooms = self.env.cache.get_default_rooms()
        if default_rooms is not None:
            return default_rooms

        default_rooms = _get_default_rooms()
        self.env.cache.set_default_rooms(default_rooms)
        return default_rooms

    def _remove_current_rooms_for_user(self, user_id: str, room_sids: dict, session):
        user = session.query(Users).filter(Users.uuid == user_id).first()
        if user is None:
            return

        rooms = session.query(Rooms)\
            .join(Rooms.users)\
            .filter(Users.uuid == user_id)\
            .all()

        if rooms is None or len(rooms) == 0:
            return

        for room in rooms:
            # have other sessions in the room
            if room.uuid in room_sids and len(room_sids[room.uuid]) > 0:
                continue

            try:
                room.users.remove(user)
            except ValueError:
                # happens if the user already left a room
                pass

        try:
            session.commit()
        except StaleDataError:
            # might have just been removed by another node
            session.rollback()

        self.env.cache.remove_rooms_for_user(user_id)

    def get_channels(self) -> dict:
        @with_session
        def _get_channels(session=None):
            rows = session.query(Channels).all()
            _channels = dict()
            for row in rows:
                if row.name == ConfigKeys.DEFAULT_CHANNEL_NAME:
                    continue
                _channels[row.uuid] = (row.name, row.sort_order, row.tags)
            return _channels

        channels = self.env.cache.get_channels_with_sort()
        if channels is not None:
            return channels

        channels = _get_channels()
        self.env.cache.set_channels_with_sort(channels)
        return channels

    @with_session
    def channel_name_exists(self, channel_name: str, session=None) -> bool:
        rows = session.query(Channels).filter(Channels.name == channel_name).all()
        return rows is not None and len(rows) > 0

    def room_name_exists(self, channel_id, room_name: str) -> bool:
        @with_session
        def _room_name_exists(session=None):
            rows = session.query(Rooms).filter(Rooms.name == room_name).all()
            exists = len(rows) > 0

            # only set in cache if actually exists, otherwise duplicates could be created
            if exists:
                self.env.cache.set_room_id_for_name(channel_id, room_name, rows[0].uuid)

            return exists

        exists = self.env.cache.get_room_id_for_name(channel_id, room_name)
        if exists is not None:
            return exists

        return _room_name_exists()

    def get_room_id_for_name(self, room_name: str, use_default_channel: bool = False) -> str:
        @with_session
        def _do_get(session=None):
            return session.query(Rooms)\
                .filter(Rooms.name == room_name)\
                .all()

        default_channel_id = None
        if use_default_channel:
            default_channel_id = self.get_or_create_default_channel()
            room_id = self.env.cache.get_room_id_for_name(default_channel_id, room_name)

            if room_id is not None:
                return room_id

        rooms = _do_get()
        if len(rooms) == 0:
            raise NoSuchRoomException(room_name)
        if len(rooms) > 1:
            raise MultipleRoomsFoundForNameException(room_name)

        room_id = rooms[0].uuid

        if use_default_channel:
            self.env.cache.set_room_id_for_name(default_channel_id, room_name, room_id)

        return room_id

    @with_session
    def get_temp_rooms_user_is_owner_for(self, user_id: str, session=None) -> list:
        roles = session.query(RoomRoles)\
            .join(RoomRoles.room)\
            .filter(Rooms.ephemeral.is_(True))\
            .filter(RoomRoles.user_id == user_id)\
            .filter(RoomRoles.roles.ilike('%owner%'))\
            .all()
        return [role.room.uuid for role in roles or list()]

    def rename_channel(self, channel_id: str, channel_name: str) -> None:
        @with_session
        def _rename_channel(session=None):
            # already checked that it exists with get_channel_name()
            channel = session.query(Channels).filter(Channels.uuid == channel_id).first()
            channel.name = channel_name
            session.commit()

        if channel_name is None or len(channel_name.strip()) == 0:
            raise EmptyChannelNameException(channel_id)

        self.get_channel_name(channel_id)

        channel_name = channel_name.strip()
        if self.channel_name_exists(channel_name):
            raise ChannelNameExistsException(channel_name)
        _rename_channel()
        self.env.cache.set_channel_name(channel_id, channel_name)

    def rename_room(self, channel_id: str, room_id: str, room_name: str) -> None:
        @with_session
        def _rename_room(session=None):
            # already checked that it exists with get_room_name()
            room = session.query(Rooms).filter(Rooms.uuid == room_id).first()
            room.name = room_name
            session.commit()

        if room_name is None or len(room_name.strip()) == 0:
            raise EmptyRoomNameException(room_id)

        self.get_channel_name(channel_id)
        self.get_room_name(room_id)

        room_name = room_name.strip()
        if self.room_name_exists(channel_id, room_name):
            raise RoomNameExistsForChannelException(channel_id, room_name)
        _rename_room()
        self.env.cache.set_room_name(room_id, room_name)

    def channel_for_room(self, room_id: str) -> str:
        @with_session
        def _channel_for_room(session=None):
            room = session\
                .query(Rooms)\
                .join(Rooms.channel)\
                .filter(Rooms.uuid == room_id)\
                .first()

            if room is None or room.channel is None:
                raise NoSuchRoomException(room_id)
            return room.channel.uuid

        if room_id is None or room_id.strip() == '':
            raise NoSuchRoomException(room_id)

        value = self.env.cache.get_channel_for_room(room_id)
        if value is not None:
            return value

        self.get_room_name(room_id)

        channel_id = _channel_for_room()
        self.env.cache.set_channel_for_room(channel_id, room_id)
        return channel_id

    def channel_exists(self, channel_id) -> bool:
        @with_session
        def _channel_exists(session=None):
            channel = session.query(Channels).filter(Channels.uuid == channel_id).first()
            exists = channel is not None

            # only set in cache if actually exists, otherwise duplicates could be created
            if exists:
                self.env.cache.set_channel_exists(channel_id)

            return exists

        exists = self.env.cache.get_channel_exists(channel_id)
        if exists is not None:
            return exists
        return _channel_exists()

    def create_channel(self, channel_name, channel_id, user_id):
        @with_session
        def _create_channel(session=None):
            channel = Channels()
            channel.uuid = channel_id
            channel.name = channel_name
            channel.created = datetime.utcnow()
            session.add(channel)

            role = ChannelRoles()
            role.channel = channel
            role.user_id = user_id
            role.roles = RoleKeys.OWNER
            session.add(role)

            channel.roles.append(role)
            session.add(channel)
            session.commit()

            self.env.cache.set_channel_exists(channel_id)
            return channel.uuid

        if channel_name is None or len(channel_name.strip()) == 0:
            raise EmptyChannelNameException(channel_id)

        if self.channel_exists(channel_id):
            raise ChannelExistsException(channel_id)

        _create_channel()

        # is none when running tests
        if self.env.node is None or 'wio' in self.env.node:
            # no need to rest sorting, not shown in wio
            return

        self.env.cache.reset_channels_with_sort()

    def get_or_create_default_channel(self):
        @with_session
        def _get_default_channel(session=None):
            channel = session.query(Channels).filter(
                Channels.name == ConfigKeys.DEFAULT_CHANNEL_NAME
            ).first()

            if channel is not None:
                return channel.uuid

            return None

        channel_id = self.env.cache.get_default_channel_id()
        if channel_id is not None:
            return channel_id

        channel_id = _get_default_channel()
        if channel_id is None:
            channel_id = str(uuid())

            # default owner is admin id 0
            self.create_channel(ConfigKeys.DEFAULT_CHANNEL_NAME, channel_id, "0")

        self.env.cache.set_default_channel_id(channel_id)
        return channel_id

    def create_room(
            self, room_name: str, room_id: str, channel_id: str, user_id: str,
            user_name: str, ephemeral: bool=True, sort_order: int=999, is_sid_room=False
    ) -> None:
        @with_session
        def _create_room(session=None):
            channel = session.query(Channels).filter(Channels.uuid == channel_id).first()
            if channel is None:
                raise NoSuchChannelException(channel_id)

            room = Rooms()
            room.uuid = room_id
            room.name = room_name
            room.channel = channel
            room.sort_order = sort_order
            room.created = datetime.utcnow()
            room.ephemeral = ephemeral
            room.admin = False
            session.add(room)

            if self.count_cumulative_joins:
                join = Joins(
                    amount=0,
                    room_id=room_id,
                    room_name=room_name
                )
                session.add(join)

            role = RoomRoles()
            role.room = room
            role.user_id = user_id
            role.roles = RoleKeys.OWNER
            session.add(role)

            room.roles.append(role)
            session.add(role)

            channel.rooms.append(room)
            session.add(channel)

            session.commit()

        if room_name is None or len(room_name.strip()) == 0:
            raise EmptyRoomNameException(room_id)

        if self.room_exists(channel_id, room_id):
            raise RoomExistsException(room_id)

        if self.room_name_exists(channel_id, room_name):
            raise RoomNameExistsForChannelException(channel_id, room_name)
        _create_room()

        if not is_sid_room:
            self.env.cache.reset_rooms_for_channel(channel_id)
            self.set_owner(room_id, user_id)

    def update_channel_sort_order(self, channel_uuid: str, sort_order: int) -> None:
        @with_session
        def update(session=None):
            channel = session.query(Channels)\
                .filter(Channels.uuid == channel_uuid)\
                .first()

            if channel is None:
                return

            channel.sort_order = sort_order
            session.commit()

        logger.info('new sort order %s for channel %s' % (str(sort_order), channel_uuid))
        self.get_channel_name(channel_uuid)
        update()
        self.env.cache.reset_channels_with_sort()

    @with_session
    def get_all_user_ids(self, session=None) -> list:
        from sqlalchemy.orm import load_only
        users = session.query(Users)\
            .join(UserStatus, Users.uuid == UserStatus.uuid)\
            .options(load_only('uuid')).all()
        return [user.uuid for user in users]

    def update_room_sort_order(self, room_uuid: str, sort_order: int) -> None:
        @with_session
        def update(session=None):
            room = session.query(Rooms)\
                .filter(Rooms.uuid == room_uuid)\
                .first()

            if room is None:
                return

            room.sort_order = sort_order
            session.commit()

        logger.info('new sort order %s for room %s' % (str(sort_order), room_uuid))
        self.get_room_name(room_uuid)
        update()

    def remove_channel(self, channel_id: str) -> None:
        @with_session
        def get_all_rooms(session=None):
            rooms = session.query(Rooms)\
                .join(Rooms.channel)\
                .filter(Channels.uuid == channel_id)\
                .all()
            return [room.uuid for room in rooms]

        @with_session
        def do_remove_channel(session=None):
            roles = session.query(ChannelRoles).join(ChannelRoles.channel).filter(Channels.uuid == channel_id).all()
            if roles is not None and len(roles) > 0:
                for role in roles:
                    session.delete(role)
                session.commit()

            channel = session.query(Channels).filter(Channels.uuid == channel_id).first()
            session.delete(channel)
            session.commit()

        self.get_channel_name(channel_id)
        room_uuids = get_all_rooms()
        for room_uuid in room_uuids:
            self.remove_room(channel_id, room_uuid)

        try:
            do_remove_channel()
        except StaleDataError as e:
            logger.warning(
                'could not remove channel %s, got stale data, will try again: %s' % (channel_id, str(e)))
            try:
                do_remove_channel()
            except StaleDataError as e:
                logger.error(
                    'could not remove channel %s for second time, logging to sentry: %s' % (channel_id, str(e)))
                self.env.capture_exception(sys.exc_info())
            except Exception as e:
                logger.error('other error when trying to remove channel %s second try: %s' % (channel_id, str(e)))
                logger.exception(traceback.format_exc())
                self.env.capture_exception(sys.exc_info())

        self.env.cache.remove_channel_exists(channel_id)
        self.env.cache.reset_rooms_for_channel(channel_id)
        self.env.cache.reset_channels_with_sort()

    def remove_room(self, channel_id: str, room_id: str) -> None:
        @with_session
        def do_remove(session=None):
            room = session\
                .query(Rooms)\
                .join(Rooms.channel)\
                .filter(Rooms.uuid == room_id)\
                .filter(Channels.uuid == channel_id)\
                .first()

            if room is None:
                raise NoSuchRoomException(room_id)

            roles = session.query(RoomRoles).join(RoomRoles.room).filter(Rooms.uuid == room_id).all()
            if roles is not None and len(roles) > 0:
                for role in roles:
                    session.delete(role)
                session.commit()

            # remove all users from this room
            try:
                room.users[:] = []
                session.commit()
            except Exception as remove_error:
                logger.error(
                    'could not remove users from room %s (%s) because: %s' % (room_id, room_name, str(remove_error)))
                self.env.capture_exception(sys.exc_info())

            session.delete(room)
            session.commit()

        room_name = self.get_room_name(room_id)

        try:
            do_remove()
        except (StaleDataError, IntegrityError) as e:
            logger.warning('could not remove room %s (%s), will try again: %s' % (room_id, room_name, str(e)))
            try:
                do_remove()
            except (StaleDataError, IntegrityError) as e:
                logger.error(
                    'could not remove room %s (%s) for second time, logging to sentry: %s' %
                    (room_id, room_name, str(e)))
                self.env.capture_exception(sys.exc_info())
            except Exception as e:
                logger.error(
                    'other error when trying to remove room %s (%s) second try: %s' % (room_id, room_name, str(e)))
                logger.exception(traceback.format_exc())
                self.env.capture_exception(sys.exc_info())
        except NoSuchRoomException:
            # might have been deleted already
            pass

        self.env.cache.remove_room_exists(channel_id, room_id)
        self.env.cache.reset_rooms_for_channel(channel_id)
        self.env.cache.remove_room_id_for_name(room_id, room_name)

    def leave_room(self, user_id: str, room_id: str) -> None:
        @with_session
        def _leave(session=None):
            room = session.query(Rooms).filter(Rooms.uuid == room_id).first()
            if room is None:
                raise NoSuchRoomException(room_id)

            user = session.query(Users)\
                .join(Users.rooms)\
                .filter(Users.uuid == user_id)\
                .filter(Rooms.uuid == room_id)\
                .first()

            if user is None:
                # user is not in the room, so nothing to do
                return

            try:
                room.users.remove(user)
            except ValueError as e2:
                logger.warning('user %s tried to leave room but already left, ignoring: %s' % (user_id, str(e2)))
                return
            session.commit()

        if user_id is None or len(user_id.strip()) == 0:
            raise EmptyUserIdException()

        logger.info('user {} just left room {}'.format(user_id, room_id))
        self.env.cache.leave_room_for_user(user_id, room_id)
        # self.get_room_name(room_id)

        try:
            _leave()
        except ValueError as e:
            logger.warning(
                'got ValueError when leaving room, likely user (%s) already left the room (%s): %s' %
                (user_id, room_id, str(e)))
            self.env.capture_exception(sys.exc_info())
        except (StaleDataError, IntegrityError) as e:
            logger.warning(
                'db error when leaving room, likely already removed from assoc table: %s' % str(e))
            self.env.capture_exception(sys.exc_info())

    def get_user_infos(self, user_ids: set) -> dict:
        @with_session
        def _get_infos(_ids: set, session=None) -> dict:
            _users = session.query(UserInfo).filter(UserInfo.user_id.in_(_ids)).all()
            _infos = dict()

            for _user in _users:
                _infos[_user.user_id] = _user.to_dict()

            return _infos

        not_found = set()
        user_infos = dict()

        for user_id in user_ids:
            user_info = self.env.auth.get_user_info(user_id)

            if len(user_info) == 0:
                not_found.add(user_id)
                continue

            user_infos[user_id] = user_info

        for user_id in not_found:
            user_infos[user_id] = dict()

        if len(not_found) > 0:
            try:
                infos = _get_infos(not_found)
            except Exception as e:
                logger.error('could not get user infos: {}'.format(str(e)))
                logger.exception(e)
                self.env.capture_exception(sys.exc_info())
                infos = {uid: dict() for uid in not_found}

            for user_id, info in infos.items():
                user_infos[user_id] = info

        return user_infos

    def set_user_info(self, user_id: str, user_info: dict) -> None:
        @with_session
        def _set_user_info(session=None):
            info = session.query(UserInfo).filter(UserInfo.user_id == user_id).first()
            if info is None:
                info = UserInfo()
                info.user_id = user_id

            info.avatar = user_info.get(SessionKeys.avatar.value)
            info.app_avatar = user_info.get(SessionKeys.app_avatar.value)
            info.app_avatar_safe = user_info.get(SessionKeys.app_avatar_safe.value)
            info.age = user_info.get(SessionKeys.age.value)
            info.gender = user_info.get(SessionKeys.gender.value)
            info.membership = user_info.get(SessionKeys.membership.value)
            info.group = user_info.get(SessionKeys.group.value)
            info.country = user_info.get(SessionKeys.country.value)
            info.has_webcam = user_info.get(SessionKeys.has_webcam.value)
            info.fake_checked = user_info.get(SessionKeys.fake_checked.value)
            info.is_streaming = user_info.get(SessionKeys.is_streaming.value)
            info.enabled_safe = user_info.get(SessionKeys.enabled_safe.value)
            info.last_login = user_info.get('last_login')

            session.add(info)
            session.commit()

        try:
            _set_user_info()
        except Exception as e:
            logger.error('could not set user info for user {}: {}'.format(user_id, str(e)))
            logger.exception(e)
            self.env.capture_exception(sys.exc_info())

    def join_room(self, user_id: str, user_name: str, room_id: str, room_name: str, sid=None) -> None:
        self.get_room_name(room_id)

        @with_session
        def _join_room(session=None):
            room = session.query(Rooms).filter(Rooms.uuid == room_id).first()
            user = session.query(Users).filter(Users.uuid == user_id).first()
            if user is None:
                user = Users()
                user.uuid = user_id
                user.name = user_name
                session.add(user)

            if room is None:
                logger.error('no such room %s (%s)' % (room_id, room_name))
                raise NoSuchRoomException(room_id)

            user.rooms.append(room)
            session.add(room)

            room.users.append(user)
            session.add(room)
            session.commit()

        @with_session
        def _save_sid_in_room(session=None):
            room_sid = RoomSids()
            room_sid.user_id = user_id
            room_sid.room_id = room_id
            room_sid.session_id = sid
            session.add(room_sid)
            session.commit()

        if sid is None:
            try:
                sid = self.env.request.sid
            except Exception as e:
                logger.error('could not get sid from request: {}'.format(str(e)))

        if sid is not None:
            try:
                _save_sid_in_room()
            except Exception as e:
                logger.error('could not save RoomSids for user {}, room {}, sid {}: {}'.format(
                    user_id, room_id, sid, str(e)
                ))

        try:
            _join_room()
        except UnmappedInstanceError as e:
            error_msg = 'user "%s" (%s) tried to join room "%s" (%s), but the room was None when joining; ' \
                        'likely removed after check and before joining: %s'
            logger.warning(error_msg % (user_id, user_name, room_id, room_name, str(e)))
        except IntegrityError as e:
            # try one more time, might have been temporary
            logger.error('could not join room "{}" ({}), got IntegrityError, will try one more time: {}'.format(
                room_name, room_id, str(e))
            )

            try:
                _join_room()
            except UnmappedInstanceError as e1:
                error_msg = 'user "%s" (%s) tried to join room "%s" (%s), but the room was None when joining; ' \
                            'likely removed after check and before joining: %s'
                logger.warning(error_msg % (user_id, user_name, room_id, room_name, str(e1)))
            except IntegrityError as e1:
                logger.warning('user "%s" (%s) tried to join room "%s" (%s) but it has been deleted: %s' %
                               (user_name, user_id, room_name, room_id, str(e1)))
                raise NoSuchRoomException(room_id)

        self.env.cache.set_user_in_room(user_id, room_id, room_name)

    def _add_global_role(self, user_id: str, role: str):
        @with_session
        def _add(session=None):
            global_role = session.query(GlobalRoles).filter(GlobalRoles.user_id == user_id).first()
            if global_role is None:
                global_role = GlobalRoles()
                global_role.user_id = user_id
                global_role.roles = role
                session.add(global_role)
                session.commit()
                return

            roles = set(global_role.roles.split(','))
            if role in roles:
                return

            roles.add(role)
            global_role.roles = ','.join(roles)
            session.commit()

        _add()
        self._update_user_roles_in_cache(user_id)

    def _remove_global_role(self, user_id: str, role: str):
        @with_session
        def _remove(session=None):
            global_role = session.query(GlobalRoles).filter(GlobalRoles.user_id == user_id).first()
            if global_role is None:
                return

            roles = set(global_role.roles.split(','))
            if role not in roles:
                return

            roles.remove(role)
            global_role.roles = ','.join(roles)
            session.commit()

        _remove()
        self._update_user_roles_in_cache(user_id)

    def _has_global_role(self, user_id: str, role: str):
        user_roles = self.get_user_roles(user_id)
        return role in user_roles['global']

    def _room_has_role_for_user(self, the_role: str, room_id: str, user_id: str) -> bool:
        user_roles = self.get_user_roles(user_id)
        return room_id in user_roles['room'] and the_role in user_roles['room'][room_id]

    def _channel_has_role_for_user(self, the_role: str, channel_id: str, user_id: str) -> bool:
        user_roles = self.get_user_roles(user_id)
        return channel_id in user_roles['channel'] and the_role in user_roles['channel'][channel_id]

    def _remove_role_on_room_for_user(self, the_role: str, room_id: str, user_id: str) -> None:
        @with_session
        def _remove(session=None):
            room = session.query(Rooms).outerjoin(Rooms.roles).filter(Rooms.uuid == room_id).first()
            if room is None:
                raise NoSuchRoomException(room_id)

            for role in room.roles:
                if role.user_id != user_id or the_role not in role.roles:
                    continue
                roles = set(role.roles.split(','))
                roles.remove(the_role)
                if len(roles) > 0:
                    role.roles = ','.join(roles)
                else:
                    session.delete(role)
                session.commit()
                return

        _remove()
        self._update_user_roles_in_cache(user_id)

    def _remove_role_on_channel_for_user(self, the_role: str, channel_id: str, user_id: str) -> None:
        @with_session
        def _remove(session=None):
            channel = session.query(Channels).outerjoin(Channels.roles).filter(Channels.uuid == channel_id).first()
            if channel is None:
                raise NoSuchChannelException(channel_id)

            for role in channel.roles:
                if role.user_id != user_id or the_role not in role.roles:
                    continue
                roles = set(role.roles.split(','))
                roles.remove(the_role)
                if len(roles) > 0:
                    role.roles = ','.join(roles)
                else:
                    session.delete(role)
                session.commit()
                return

        _remove()
        self._update_user_roles_in_cache(user_id)

    def _set_role_on_room_for_user(self, the_role: Rooms, room_id: str, user_id: str) -> None:
        @with_session
        def _set(session=None):
            room = session.query(Rooms).outerjoin(Rooms.roles).filter(Rooms.uuid == room_id).first()
            if room is None:
                raise NoSuchRoomException(room_id)

            found_role = None
            for role in room.roles:
                if role.user_id == user_id:
                    found_role = role
                    if the_role in role.roles:
                        return

            if found_role is None:
                found_role = RoomRoles()
                found_role.user_id = user_id
                found_role.room = room
                found_role.roles = the_role
            else:
                roles = set(found_role.roles.split(','))
                roles.add(the_role)
                found_role.roles = ','.join(roles)

            session.add(found_role)
            session.commit()

        _set()
        self._update_user_roles_in_cache(user_id)
        self.env.cache.reset_users_in_room_for_role(room_id, the_role)

    def _set_role_on_channel_for_user(self, the_role: str, channel_id: str, user_id: str) -> None:
        @with_session
        def _set(session=None):
            channel = session.query(Channels).outerjoin(Channels.roles).filter(Channels.uuid == channel_id).first()
            if channel is None:
                raise NoSuchChannelException(channel_id)

            found_role = None
            for role in channel.roles:
                if role.user_id != user_id:
                    continue
                found_role = role
                if the_role in role.roles:
                    return

            if found_role is None:
                found_role = ChannelRoles()
                found_role.user_id = user_id
                found_role.channel = channel
                found_role.roles = the_role
            else:
                roles = set(found_role.roles.split(','))
                roles.add(the_role)
                found_role.roles = ','.join(roles)

            session.add(found_role)
            session.commit()

        _set()
        self._update_user_roles_in_cache(user_id)
        self.env.cache.reset_users_in_channel_for_role(channel_id, the_role)

    def set_super_user(self, user_id: str) -> None:
        self._add_global_role(user_id, RoleKeys.SUPER_USER)

    def remove_super_user(self, user_id: str) -> None:
        self._remove_global_role(user_id, RoleKeys.SUPER_USER)

    def is_super_user(self, user_id: str) -> bool:
        return self._has_global_role(user_id, RoleKeys.SUPER_USER)

    def is_moderator(self, room_id: str, user_id: str) -> bool:
        return self._room_has_role_for_user(RoleKeys.MODERATOR, room_id, user_id)

    def is_global_moderator(self, user_id: str) -> bool:
        return self._has_global_role(user_id, RoleKeys.GLOBAL_MODERATOR)

    def is_admin(self, channel_id: str, user_id: str) -> bool:
        return self._channel_has_role_for_user(RoleKeys.ADMIN, channel_id, user_id)

    def is_owner(self, room_id: str, user_id: str) -> bool:
        return self._room_has_role_for_user(RoleKeys.OWNER, room_id, user_id)

    def is_owner_channel(self, channel_id: str, user_id: str) -> bool:
        return self._channel_has_role_for_user(RoleKeys.OWNER, channel_id, user_id)

    def set_admin(self, channel_id: str, user_id: str) -> None:
        self._set_role_on_channel_for_user(RoleKeys.ADMIN, channel_id, user_id)

    def set_moderator(self, room_id: str, user_id: str) -> None:
        self._set_role_on_room_for_user(RoleKeys.MODERATOR, room_id, user_id)

    def set_global_moderator(self, user_id: str) -> None:
        self._add_global_role(user_id, RoleKeys.GLOBAL_MODERATOR)

    def set_owner(self, room_id: str, user_id: str) -> None:
        self._set_role_on_room_for_user(RoleKeys.OWNER, room_id, user_id)

    def set_owner_channel(self, channel_id: str, user_id: str) -> None:
        self._set_role_on_channel_for_user(RoleKeys.OWNER, channel_id, user_id)

    def remove_admin(self, channel_id: str, user_id: str) -> None:
        self._remove_role_on_channel_for_user(RoleKeys.ADMIN, channel_id, user_id)

    def remove_owner_channel(self, channel_id: str, user_id: str) -> None:
        self._remove_role_on_channel_for_user(RoleKeys.OWNER, channel_id, user_id)

    def remove_moderator(self, room_id: str, user_id: str) -> None:
        self._remove_role_on_room_for_user(RoleKeys.MODERATOR, room_id, user_id)

    def remove_global_moderator(self, user_id: str) -> None:
        self._remove_global_role(user_id, RoleKeys.GLOBAL_MODERATOR)

    def remove_owner(self, room_id: str, user_id: str) -> None:
        self._remove_role_on_room_for_user(RoleKeys.OWNER, room_id, user_id)

    def delete_acl_in_room_for_action(self, room_id: str, acl_type: str, action: str) -> None:
        @with_session
        def do_delete(session=None):
            room = session.query(Rooms).filter(Rooms.uuid == room_id).first()
            if room is None:
                raise NoSuchRoomException(room_id)

            found_acl = session.query(Acls)\
                .join(Acls.room)\
                .filter(Acls.acl_type == acl_type)\
                .filter(Rooms.uuid == room_id).first()

            if found_acl is None:
                return

            session.delete(found_acl)
            session.commit()

        if action not in ApiActions.all_api_actions:
            raise InvalidApiActionException(action)
        do_delete()
        self.env.cache.reset_acls_in_room_for_action(room_id, action)
        self.env.cache.reset_acls_in_room(room_id)

    def delete_acl_in_channel_for_action(self, channel_id: str, acl_type: str, action: str, session=None) -> None:
        @with_session
        def do_delete(session=None):
            channel = session.query(Channels).filter(Channels.uuid == channel_id).first()
            if channel is None:
                raise NoSuchChannelException(channel_id)

            found_acl = session.query(Acls)\
                .join(Acls.channel)\
                .filter(Acls.acl_type == acl_type)\
                .filter(Channels.uuid == channel_id).first()

            if found_acl is None:
                return

            session.delete(found_acl)
            session.commit()

        if action not in ApiActions.all_api_actions:
            raise InvalidApiActionException(action)
        do_delete()
        self.env.cache.reset_acls_in_channel_for_action(channel_id, action)
        self.env.cache.reset_acls_in_channel(channel_id)

    def add_acls_in_room_for_action(self, room_id: str, action: str, new_acls: dict) -> None:
        @with_session
        def _add_acls_in_room_for_action(session=None):
            room = session.query(Rooms)\
                .outerjoin(Rooms.acls)\
                .filter(Rooms.uuid == room_id)\
                .first()

            existing_acls = room.acls
            to_add = self._add_acls(existing_acls, new_acls, action, ApiTargets.ROOM)

            for acl in to_add:
                acl.room = room
                session.add(acl)

            session.commit()

        if new_acls is None or len(new_acls) == 0:
            return

        self.get_room_name(room_id)
        _add_acls_in_room_for_action()
        self.env.cache.reset_acls_in_room_for_action(room_id, action)
        self.env.cache.reset_acls_in_room(room_id)

    def add_acls_in_channel_for_action(self, channel_id: str, action: str, new_acls: dict) -> None:
        @with_session
        def _add_acls_in_channel_for_action(session=None):
            channel = session.query(Channels)\
                .outerjoin(Channels.acls)\
                .filter(Channels.uuid == channel_id)\
                .first()

            existing_acls = channel.acls
            to_add = self._add_acls(existing_acls, new_acls, action, ApiTargets.CHANNEL)

            for acl in to_add:
                acl.channel = channel
                session.add(acl)

            session.commit()

        if new_acls is None or len(new_acls) == 0:
            return

        self.get_channel_name(channel_id)
        _add_acls_in_channel_for_action()
        self.env.cache.reset_acls_in_channel_for_action(channel_id, action)
        self.env.cache.reset_acls_in_channel(channel_id)

    def _add_acls(self, existing_acls: list, new_acls: dict, action: str, target: str) -> (list, list):
        updated_acls = set()
        if existing_acls is not None and len(existing_acls) > 0:
            for acl in existing_acls:
                if acl.action != action:
                    continue
                if acl.acl_type not in new_acls.keys():
                    continue

                new_value = new_acls[acl.acl_type]
                acl.acl_value = new_value
                updated_acls.add(acl.acl_type)

        to_add = list()
        for acl_type, acl_value in new_acls.items():
            # already deleted/updated
            if acl_type in updated_acls:
                continue

            if acl_type not in self._get_acls_for_target_and_action(target, action):
                raise InvalidAclTypeException(acl_type)

            is_valid, error_msg = self._validate_acl_for_target_and_action(target, action, acl_type, acl_value)
            if not is_valid:
                raise ValidationException(error_msg)

            acl = Acls()
            acl.action = action
            acl.acl_type = acl_type
            acl.acl_value = acl_value
            to_add.append(acl)

        return to_add

    def _validate_acl_for_target_and_action(self, target: str, action: str, acl_type: str, acl_value: str):
        validators = self._get_acls_for_target('validation')
        try:
            validators[acl_type]['value'].validate_new_acl(acl_value)
        except ValidationException as e:
            logger.info('new acl values "%s" did not validate for type "%s": %s' % (acl_value, acl_type, e.msg))
            return False, e.msg
        return True, None

    def _get_acls(self) -> dict:
        return self.env.config.get(ConfigKeys.ACL)

    def _get_acls_for_target(self, target: str) -> dict:
        return self._get_acls().get(target)

    def _get_acls_for_target_and_action(self, target, action) -> list:
        acls_for_target = self._get_acls_for_target(target)
        if acls_for_target is None:
            return list()

        if action not in acls_for_target:
            raise InvalidApiActionException(action)

        acls_for_action = acls_for_target.get(action)
        if acls_for_action is None:
            return list()

        acls = acls_for_action.get('acls')
        if acls is None:
            return list()
        return acls

    def update_acl_in_room_for_action(self, channel_id: str, room_id: str, action: str, acl_type: str, acl_value: str) -> None:
        self.get_channel_name(channel_id)
        self.add_acls_in_room_for_action(room_id, action, {acl_type: acl_value})

    def update_acl_in_channel_for_action(self, channel_id: str, action: str, acl_type: str, acl_value: str) -> None:
        self.add_acls_in_channel_for_action(channel_id, action, {acl_type: acl_value})

    def get_acl_validation_value(self, acl_type: str, validation_method: str) -> str:
        @with_session
        def get_value(session=None):
            return session.query(AclConfigs)\
                .filter(AclConfigs.acl_type == acl_type)\
                .filter(AclConfigs.method == validation_method)\
                .first()

        if acl_type is None or len(acl_type.strip()) == 0:
            raise InvalidAclTypeException(acl_type)

        if validation_method is None or len(validation_method.strip()) == 0:
            raise InvalidAclValueException(acl_type, validation_method)

        acl_config = get_value()
        if acl_config is None or acl_config.acl_value is None or len(acl_config.acl_value.strip()) == 0:
            raise AclValueNotFoundException(acl_type, validation_method)

        return acl_config.acl_value

    def get_all_acls_channel(self, channel_id: str) -> dict:
        @with_session
        def _acls(session=None):
            channel = session.query(Channels)\
                .outerjoin(Channels.acls)\
                .filter(Channels.uuid == channel_id)\
                .first()

            if channel is None:
                raise NoSuchChannelException(channel_id)

            found_acls = channel.acls
            if found_acls is None or len(found_acls) == 0:
                return dict()

            acls = dict()
            for acl in found_acls:
                if acl.action not in acls:
                    acls[acl.action] = dict()
                acls[acl.action][acl.acl_type] = acl.acl_value
            return acls

        value = self.env.cache.get_all_acls_for_channel(channel_id)
        if value is not None:
            return value
        value = _acls()
        self.env.cache.set_all_acls_for_channel(channel_id, value)
        return value

    def get_all_acls_room(self, room_id: str) -> dict:
        @with_session
        def _acls(session=None):
            room = session.query(Rooms)\
                .outerjoin(Rooms.acls)\
                .filter(Rooms.uuid == room_id)\
                .first()

            if room is None:
                return None

            found_acls = room.acls
            if found_acls is None or len(found_acls) == 0:
                return dict()

            acls = dict()
            for acl in found_acls:
                if acl.action not in acls:
                    acls[acl.action] = dict()
                acls[acl.action][acl.acl_type] = acl.acl_value
            return acls

        value = self.env.cache.get_all_acls_for_room(room_id)
        if value is not None:
            return value

        value = _acls()
        if value is None:
            raise NoSuchRoomException(room_id)

        self.env.cache.set_all_acls_for_room(room_id, value)
        return value

    def get_room_acls_for_action(self, action) -> Dict[str, Dict[str, str]]:
        @with_session
        def _acls(session=None):
            rooms = session.query(Rooms)\
                .join(Rooms.acls)\
                .filter(Acls.action == action)\
                .all()

            if rooms is None or len(rooms) == 0:
                return dict()

            room_acls = dict()

            for room in rooms:
                acls = dict()
                found_acls = room.acls

                if found_acls is None or len(found_acls) == 0:
                    acls[room.uuid] = dict()

                for found_acl in found_acls:
                    if found_acl.action == action:
                        acls[found_acl.acl_type] = found_acl.acl_value

                room_acls[room.uuid] = acls

            return room_acls

        value = self.env.cache.get_room_acls_for_action(action)
        if value is not None:
            return value
        value = _acls()
        self.env.cache.set_room_acls_for_action(action, value)
        return value

    def get_acls_in_room_for_action(self, room_id: str, action: str):
        @with_session
        def _acls(session=None):
            room = session.query(Rooms)\
                .outerjoin(Rooms.acls)\
                .filter(Rooms.uuid == room_id)\
                .first()

            if room is None:
                raise NoSuchRoomException(room_id)

            found_acls = room.acls
            if found_acls is None or len(found_acls) == 0:
                return dict()

            acls = dict()
            for found_acl in found_acls:
                if found_acl.action != action:
                    continue
                acls[found_acl.acl_type] = found_acl.acl_value
            return acls

        value = self.env.cache.get_acls_in_room_for_action(room_id, action)
        if value is not None:
            return value
        value = _acls()
        self.env.cache.set_acls_in_room_for_action(room_id, action, value)
        return value

    def get_acls_in_channel_for_action(self, channel_id: str, action: str):
        @with_session
        def _acls(session=None):
            channel = session.query(Channels)\
                .outerjoin(Channels.acls)\
                .filter(Channels.uuid == channel_id)\
                .first()

            if channel is None:
                raise NoSuchChannelException(channel_id)

            found_acls = channel.acls
            if found_acls is None or len(found_acls) == 0:
                return dict()

            acls = dict()
            for found_acl in found_acls:
                if found_acl.action != action:
                    continue
                acls[found_acl.acl_type] = found_acl.acl_value
            return acls

        value = self.env.cache.get_acls_in_channel_for_action(channel_id, action)
        if value is not None:
            return value
        value = _acls()
        self.env.cache.set_acls_in_channel_for_action(channel_id, action, value)
        return value

    def _format_spam(self, spam: Spams) -> dict:
        if spam is None:
            return dict()

        return {
            'id': spam.id,
            'from_id': spam.from_uid,
            'from_name': spam.from_name,
            'to_id': spam.to_uid,
            'to_name': spam.to_name,
            'time_stamp': spam.time_stamp,
            'message': spam.message,
            'message_id': spam.message_id,
            'message_deleted': spam.message_deleted,
            'object_type': spam.object_type,
            'probability': spam.probability,
            'correct': spam.correct
        }

    @with_session
    def mark_spam_deleted_if_exists(self, message_id: str, session=None) -> None:
        spam = session.query(Spams).filter(Spams.message_id == message_id).first()
        if spam is not None:
            spam.message_deleted = True
            session.add(spam)
            session.commit()

    @with_session
    def mark_spam_not_deleted_if_exists(self, message_id: str, session=None) -> None:
        spam = session.query(Spams).filter(Spams.message_id == message_id).first()
        if spam is not None:
            spam.message_deleted = False
            session.add(spam)
            session.commit()

    @with_session
    def get_spam(self, spam_id: int, session=None) -> dict:
        spam = session.query(Spams).filter(Spams.id == spam_id).first()
        return self._format_spam(spam)

    @with_session
    def get_latest_spam(self, limit: int, session=None) -> list:
        return [
            self._format_spam(spam)
            for spam in session.query(Spams).order_by(Spams.time_stamp.desc()).limit(limit).all()
        ]

    @with_session
    def get_spam_for_time_slice(self, room_id, user_id, from_time_int, to_time_int, session=None) -> list:
        if room_id is not None:
            spams = session.query(Spams)\
                .filter(from_time_int <= Spams.time_stamp)\
                .filter(Spams.time_stamp <= to_time_int)\
                .filter(Spams.to_uid == room_id)\
                .all()

        elif user_id is not None:
            spams = session.query(Spams)\
                .filter(from_time_int <= Spams.time_stamp <= to_time_int)\
                .filter(Spams.from_uid == user_id)\
                .all()

        else:
            spams = session.query(Spams)\
                .filter(from_time_int <= Spams.time_stamp <= to_time_int)\
                .all()

        return [self._format_spam(spam) for spam in spams]

    @with_session
    def get_spam_from(self, user_id: str, session=None) -> list:
        return [
            self._format_spam(spam)
            for spam in session.query(Spams).filter(Spams.from_uid == user_id).all()
        ]

    @with_session
    def update_spam_config(
            self, enabled, max_length, min_length, should_delete,
            should_save, threshold, ignore_emoji, session=None
    ) -> None:
        config = session.query(Config).first()

        if enabled is not None:
            config.spam_enabled = enabled

        if max_length is not None:
            if max_length <= 0:
                raise ValueError('max length needs to be >0')
            config.spam_spam_max_length = max_length

        if min_length is not None:
            if min_length < 0:
                raise ValueError('min length needs to be positive')
            config.spam_min_length = min_length

        if ignore_emoji is not None:
            config.spam_ignore_emoji = ignore_emoji

        if threshold is not None:
            config.spam_threshold = threshold

        if should_delete is not None:
            config.spam_should_delete = should_delete

        if should_save is not None:
            config.spam_should_save = should_save

        session.add(config)
        session.commit()

    @with_session
    def disable_spam_classifier(self, session=None) -> None:
        config = session.query(Config).first()
        config.spam = False
        session.add(config)
        session.commit()

    @with_session
    def enable_spam_classifier(self, session=None) -> None:
        config = session.query(Config).first()
        config.spam = True
        session.add(config)
        session.commit()

    @with_session
    def set_spam_min_length(self, min_length: int, session=None) -> None:
        if min_length < 0:
            raise ValueError('min length needs to be positive')

        config = session.query(Config).first()
        config.spam_min_length = min_length
        session.add(config)
        session.commit()

    @with_session
    def set_spam_max_length(self, max_length: int, session=None) -> None:
        if max_length <= 0:
            raise ValueError('max length needs to be >0')

        config = session.query(Config).first()
        config.spam_max_length = max_length
        session.add(config)
        session.commit()

    @with_session
    def enable_spam_delete(self, session=None) -> None:
        config = session.query(Config).first()
        config.spam_should_delete = True
        session.add(config)
        session.commit()

    @with_session
    def disable_spam_delete(self, session=None) -> None:
        config = session.query(Config).first()
        config.spam_should_delete = False
        session.add(config)
        session.commit()

    @with_session
    def enable_spam_save(self, session=None) -> None:
        config = session.query(Config).first()
        config.spam_should_save = True
        session.add(config)
        session.commit()

    @with_session
    def disable_spam_save(self, session=None) -> None:
        config = session.query(Config).first()
        config.spam_should_save = False
        session.add(config)
        session.commit()

    @with_session
    def set_spam_correct_or_not(self, spam_id: int, correct: bool, session=None):
        spam = session.query(Spams).filter(Spams.id == spam_id).first()
        spam.correct = correct
        session.add(spam)
        session.commit()

    @with_session
    def save_spam_prediction(self, activity: Activity, message, y_hats: tuple, session=None):
        to_name = activity.target.display_name
        from_name = activity.actor.display_name

        if is_base64(to_name):
            try:
                to_name = b64d(to_name)
            except Exception:
                pass
        if is_base64(from_name):
            try:
                from_name = b64d(from_name)
            except Exception:
                pass

        spam = Spams()
        spam.time_stamp = int(datetime.utcnow().strftime('%s'))
        spam.from_name = from_name
        spam.from_uid = activity.actor.id
        spam.to_name = to_name
        spam.to_uid = activity.target.id
        spam.object_type = activity.target.object_type
        spam.message = message
        spam.message_deleted = self.env.service_config.is_spam_classifier_enabled()
        spam.message_id = activity.id
        spam.probability = ','.join([str(y_hat) for y_hat in y_hats])

        session.add(spam)
        session.commit()

        logger.info('saved spam prediction to db with ID {}'.format(spam.id))

    @with_session
    def update_last_read_for(self, users: set, room_id: str, time_stamp: int, session=None) -> None:
        for user_id in users:
            last_read = session.query(LastReads)\
                .filter(LastReads.user_id == user_id)\
                .filter(LastReads.room_uuid == room_id)\
                .first()

            if last_read is None:
                last_read = LastReads()
                last_read.room_uuid = room_id
                last_read.user_id = user_id

            last_read.time_stamp = time_stamp
            session.add(last_read)
        session.commit()

    @with_session
    def get_last_read_timestamp(self, room_id: str, user_id: str, session=None) -> int:
        last_read = session.query(LastReads)\
            .filter(LastReads.user_id == user_id)\
            .filter(LastReads.room_uuid == room_id)\
            .first()

        if last_read is None:
            return None

        return last_read.time_stamp

    def set_user_name(self, user_id: str, user_name: str):
        @with_session
        def update_if_exists(session=None):
            user = session.query(Users).filter(Users.uuid == user_id).first()
            if user is None:
                return False
            user.name = user_name
            session.add(user)
            session.commit()
            return True

        if not update_if_exists():
            self.create_user(user_id, user_name)
        self.env.cache.set_user_name(user_id, user_name)

    def create_user(self, user_id: str, user_name: str) -> None:
        @with_session
        def _create_user(session=None):
            user = Users()
            user.uuid = user_id
            user.name = user_name
            session.add(user)
            session.commit()

        if user_name is None or len(user_name.strip()) == 0:
            raise EmptyUserNameException(user_id)

        if user_id is None or len(user_id.strip()) == 0:
            raise EmptyUserIdException()

        try:
            username = self.get_user_name(user_id, skip_cache=True)
            if username is not None:
                raise UserExistsException(user_id)
        except NoSuchUserException:
            pass
        _create_user()

    @with_session
    def get_super_users(self, session=None) -> dict:
        roles = session.query(GlobalRoles)\
            .filter(GlobalRoles.roles.like('%{}%'.format(RoleKeys.SUPER_USER)))\
            .all()

        if roles is None or len(roles) == 0:
            return dict()

        users = dict()
        for role in roles:
            users[role.user_id] = self.get_user_name(role.user_id)
        return users

    def user_name_exists(self, user_name: str) -> bool:
        @with_session
        def _user_name_exists(session=None):
            user = session.query(Users).filter(Users.name == user_name).first()
            return user is not None

        if self.env.cache.get_user_name_exists(user_name):
            return True

        exists = _user_name_exists()
        if exists:
            self.env.cache.set_user_name_exists(user_name)

        return exists

    def get_user_id(self, user_name: str) -> str:
        @with_session
        def _get_user_name(session=None):
            user = session.query(Users).filter(Users.name == user_name).first()
            if user is None:
                return None
            return user.uuid

        user_id = self.env.cache.get_user_id(user_name)
        if user_id is not None and len(user_id.strip()) > 0:
            return user_id

        user_id = _get_user_name()
        if user_id is not None and len(user_id.strip()) > 0:
            self.env.cache.set_user_id(user_id, user_name)

        if user_id is None or len(user_id.strip()) == 0:
            raise NoSuchUserException(user_name)

        return user_id

    def get_user_name(self, user_id: str, skip_cache=False) -> str:
        @with_session
        def _get_user_name(session=None):
            user = session.query(Users).filter(Users.uuid == user_id).first()
            if user is None:
                return None
            return user.name

        if skip_cache:
            user_name = _get_user_name()
            if user_name is None or len(user_name.strip()) == 0:
                raise NoSuchUserException(user_id)
            return user_name

        user_name = self.env.cache.get_user_name(user_id)
        if user_name is not None and len(user_name.strip()) > 0:
            return user_name

        user_name = _get_user_name()
        if user_name is not None and len(user_name.strip()) > 0:
            self.env.cache.set_user_name(user_id, user_name)

        if user_name is None or len(user_name.strip()) == 0:
            raise NoSuchUserException(user_id)

        return user_name

    def _get_users_with_role(self, roles, role_key):
        if roles is None or len(roles) == 0:
            return dict()

        found = dict()
        for role in roles:
            if role_key not in role.roles.split(','):
                continue

            try:
                found[role.user_id] = self.get_user_name(role.user_id)
            except NoSuchUserException as e:
                logger.exception(traceback.format_exc())
                logger.error('no username found for user_id %s: %s' % (role.user_id, str(e)))
        return found

    def _get_users_with_role_in_channel(self, channel_id: str, role_key: str) -> dict:
        @with_session
        def _roles(session=None):
            return session.query(ChannelRoles).join(ChannelRoles.channel).filter(Channels.uuid == channel_id).all()

        roles = self.env.cache.get_users_in_channel_for_role(channel_id, role_key)
        if roles is not None:
            return roles

        roles = self._get_users_with_role(_roles(), role_key)
        self.env.cache.set_users_in_channel_for_role(channel_id, role_key, roles)
        return roles

    def _get_users_with_role_in_room(self, room_id: str, role_key: str) -> dict:
        @with_session
        def _roles(session=None):
            return session.query(RoomRoles).join(RoomRoles.room).filter(Rooms.uuid == room_id).all()

        roles = self.env.cache.get_users_in_room_for_role(room_id, role_key)
        if roles is not None:
            return roles

        roles = self._get_users_with_role(_roles(), role_key)
        self.env.cache.set_users_in_room_for_role(room_id, role_key, roles)
        return roles

    def get_owners_channel(self, channel_id: str) -> dict:
        return self._get_users_with_role_in_channel(channel_id, RoleKeys.OWNER)

    def get_admins_channel(self, channel_id: str) -> dict:
        return self._get_users_with_role_in_channel(channel_id, RoleKeys.ADMIN)

    def get_owners_room(self, room_id: str) -> dict:
        return self._get_users_with_role_in_room(room_id, RoleKeys.OWNER)

    def get_avatars_for(self, user_ids: set) -> dict:
        @with_session
        def _get_user_info(_user_id, session=None) -> UserInfo:
            return session.query(UserInfo).filter(UserInfo.user_id == _user_id).first()

        user_to_avatar = dict()

        for user_id in user_ids:
            avatar_url, app_avatar_url, app_avatar_safe_url = '', '', ''
            avatars = self.env.cache.get_avatar_for(user_id)

            if avatars is None:
                avatar = _get_user_info(user_id)
                if avatar is not None:
                    avatar_url = avatar.avatar
                    app_avatar_url = avatar.app_avatar
                    app_avatar_safe_url = avatar.app_avatar_safe
                    self.env.cache.set_avatar_for(
                        user_id,
                        avatar_url,
                        app_avatar_url,
                        app_avatar_safe_url
                    )
            else:
                avatar_url, app_avatar_url, app_avatar_safe_url = avatars

            user_to_avatar[user_id] = (avatar_url, app_avatar_url, app_avatar_safe_url)
        return user_to_avatar

    def get_moderators_room(self, room_id: str) -> dict:
        return self._get_users_with_role_in_room(room_id, RoleKeys.MODERATOR)

    def get_room_name(self, room_id: str) -> str:
        @with_session
        def _get_room_name(session=None):
            room = session.query(Rooms).filter(Rooms.uuid == room_id).first()
            if room is None:
                raise NoSuchRoomException(room_id)
            return room.name

        value = self.env.cache.get_room_name(room_id)
        if value is not None:
            return value

        try:
            value = _get_room_name()
        except NoSuchRoomException as e:
            raise e

        self.env.cache.set_room_name(room_id, value)
        return value

    def get_channel_name(self, channel_id: str) -> str:
        @with_session
        def _get_channel_name(session=None):
            channel = session.query(Channels).filter(Channels.uuid == channel_id).first()
            if channel is None:
                raise NoSuchChannelException(channel_id)
            return channel.name

        value = self.env.cache.get_channel_name(channel_id)
        if value is not None:
            return value
        channel_name = _get_channel_name()
        self.env.cache.set_channel_name(channel_id, channel_name)
        return channel_name

    def is_banned_globally(self, user_id: str) -> (bool, Union[str, None]):
        now = datetime.utcnow()
        duration, time, username = self.env.cache.get_global_ban_timestamp(user_id)
        if time is not None and len(time.strip()) != 0:
            time = datetime.fromtimestamp(float(time))
            if now > time:
                self.remove_global_ban(user_id)
                return False, None
            return True, str((time-now).seconds)

        duration, time, username = self.get_global_ban_timestamp(user_id)
        if time is None:
            self.env.cache.set_global_ban_timestamp(user_id, '', '', '')
            return False, None
        if now > time:
            self.remove_global_ban(user_id)
            return False, None

        time_stamp = str(int(time.timestamp()))
        self.env.cache.set_global_ban_timestamp(user_id, duration, time_stamp, username)
        return True, str((time-now).seconds)

    def is_banned_from_channel(self, channel_id: str, user_id: str) -> (bool, Union[str, None]):
        now = datetime.utcnow()
        duration, time, username = self.env.cache.get_channel_ban_timestamp(channel_id, user_id)
        if time is not None and len(time.strip()) != 0:
            if time == '':
                return False, None

            time = datetime.fromtimestamp(float(time))
            if now > time:
                self.remove_channel_ban(channel_id, user_id)
                return False, None
            return True, str((time-now).seconds)

        duration, time, username = self.get_channel_ban_timestamp(channel_id, user_id)
        if time is None:
            self.env.cache.set_channel_ban_timestamp(channel_id, user_id, '', '', '')
            return False, None
        if now > time:
            self.remove_channel_ban(channel_id, user_id)
            return False, None

        self.env.cache.set_channel_ban_timestamp(channel_id, user_id, duration, time, username)
        return True, str((time-now).seconds)

    def is_banned_from_room(self, room_id: str, user_id: str) -> (bool, Union[str, None]):
        now = datetime.utcnow()
        duration, time, username = self.env.cache.get_room_ban_timestamp(room_id, user_id)
        if time is not None and len(time.strip()) != 0:
            if time == '':
                return False, None

            time = datetime.fromtimestamp(float(time))
            if now > time:
                self.remove_room_ban(room_id, user_id)
                return False, None
            return True, str((time-now).seconds)

        duration, time, username = self.get_room_ban_timestamp(room_id, user_id)
        if time is None:
            self.env.cache.set_room_ban_timestamp(room_id, user_id, '', '', '')
            return False, None
        if now > time:
            self.remove_room_ban(room_id, user_id)
            return False, None

        self.env.cache.set_room_ban_timestamp(room_id, user_id, duration, time, username)
        return True, str((time-now).seconds)

    @with_session
    def get_global_ban_timestamp(self, user_id: str, session=None) -> (str, str, str):
        global_ban = session.query(Bans)\
            .filter(Bans.is_global.is_(True))\
            .filter(Bans.user_id == user_id)\
            .first()

        if global_ban is not None:
            return global_ban.duration, global_ban.timestamp, global_ban.user_name
        return None, None, None

    @with_session
    def get_channel_ban_timestamp(self, channel_id: str, user_id: str, session=None) -> (str, str, str):
        channel_ban = session.query(Bans)\
            .join(Bans.channel)\
            .filter(Bans.is_global.is_(False))\
            .filter(Channels.uuid == channel_id)\
            .filter(Bans.user_id == user_id)\
            .first()

        if channel_ban is not None:
            return channel_ban.duration, channel_ban.timestamp, channel_ban.user_name
        return None, None, None

    @with_session
    def get_room_ban_timestamp(self, room_id: str, user_id: str, session=None) -> (str, str, str):
        room_ban = session.query(Bans)\
            .join(Bans.room)\
            .filter(Bans.is_global.is_(False))\
            .filter(Rooms.uuid == room_id)\
            .filter(Bans.user_id == user_id)\
            .first()

        if room_ban is not None:
            return room_ban.duration, room_ban.timestamp, room_ban.user_name
        return None, None, None

    @with_session
    def get_bans_for_user(self, user_id: str, session=None) -> dict:
        bans = session.query(Bans)\
            .outerjoin(Bans.channel)\
            .outerjoin(Bans.room)\
            .filter(Bans.user_id == user_id).all()

        output = {
            'global': dict(),
            'channel': dict(),
            'room': dict()
        }

        for ban in bans:
            if ban.room is not None:
                output['room'][ban.room.uuid] = {
                    'name': b64e(ban.room.name),
                    'duration': ban.duration,
                    'timestamp': ban.timestamp.strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
                }
            elif ban.channel is not None:
                output['channel'][ban.channel.uuid] = {
                    'name': b64e(ban.channel.name),
                    'duration': ban.duration,
                    'timestamp': ban.timestamp.strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
                }
            elif ban.is_global:
                output['global'] = {
                    'duration': ban.duration,
                    'timestamp': ban.timestamp.strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
                }
        return output

    def get_reason_for_ban_global(self, user_id: str) -> str:
        @with_session
        def _get_reason(session=None):
            ban = session.query(Bans)\
                .filter(Bans.user_id == user_id)\
                .filter(Bans.is_global.is_(True))\
                .first()
            if ban is None:
                return ''
            return ban.reason

        self.get_user_name(user_id)
        return _get_reason()

    def get_reason_for_ban_channel(self, user_id: str, channel_uuid: str) -> str:
        @with_session
        def _get_reason(session=None):
            ban = session.query(Bans)\
                .join(Bans.room)\
                .filter(Bans.user_id == user_id)\
                .filter(Bans.is_global.is_(False))\
                .filter(Channels.uuid == channel_uuid)\
                .first()
            if ban is None:
                return ''
            return ban.reason

        self.get_user_name(user_id)
        return _get_reason()

    def get_reason_for_ban_room(self, user_id: str, room_uuid: str) -> str:
        @with_session
        def _get_reason(session=None):
            ban = session.query(Bans)\
                .join(Bans.room)\
                .filter(Bans.user_id == user_id)\
                .filter(Bans.is_global.is_(False))\
                .filter(Rooms.uuid == room_uuid)\
                .first()
            if ban is None:
                return ''
            return ban.reason

        self.get_user_name(user_id)
        return _get_reason()

    def get_user_ban_status(self, room_id: str, user_id: str) -> dict:
        # TODO: fix this method, it's a horribly ugly friday night hack
        def _has_passed(the_time):
            now = datetime.utcnow()
            return now > datetime.fromtimestamp(int(float(the_time)))

        def _set_in_cache_if_none(_gtime, _ctime, _rtime):
            if _gtime is None:
                duration, _gtime, username = self.get_global_ban_timestamp(user_id)
                if _gtime is None:
                    duration, _gtime, username = '', '', ''
                else:
                    _gtime = _gtime.timestamp()
                self.env.cache.set_global_ban_timestamp(user_id, duration, _gtime, username)
            if _ctime is None:
                duration, _ctime, username = self.get_channel_ban_timestamp(channel_id, user_id)
                if _ctime is None:
                    duration, _ctime, username = '', '', ''
                else:
                    _ctime = _ctime.timestamp()
                self.env.cache.set_channel_ban_timestamp(channel_id, user_id, duration, _ctime, username)
            if _rtime is None:
                duration, _rtime, username = self.get_room_ban_timestamp(room_id, user_id)
                if _rtime is None:
                    _rtime = ''
                else:
                    _rtime = _rtime.timestamp()
                self.env.cache.set_room_ban_timestamp(room_id, user_id, duration, _rtime, username)
            return _gtime, _ctime, _rtime

        def _update_if_passed(_gtime, _ctime, _rtime):
            if _gtime is not None and _gtime != '':
                if _has_passed(_gtime):
                    self.remove_global_ban(user_id)
                    _gtime = ''
            if _ctime is not None and _ctime != '':
                if _has_passed(_ctime):
                    self.remove_channel_ban(channel_id, user_id)
                    _ctime = ''
            if _rtime is not None and _rtime != '':
                if _has_passed(_rtime):
                    self.remove_room_ban(room_id, user_id)
                    _rtime = ''
            return _gtime or '', _ctime or '', _rtime or ''

        channel_id = self.channel_for_room(room_id)
        _, gtime, _ = self.env.cache.get_global_ban_timestamp(user_id)
        _, ctime, _ = self.env.cache.get_channel_ban_timestamp(channel_id, user_id)
        _, rtime, _ = self.env.cache.get_room_ban_timestamp(room_id, user_id)

        # even if no ban, set in cache so we don't have to check db
        gtime, ctime, rtime = _set_in_cache_if_none(gtime, ctime, rtime)

        # empty string means there is no ban
        gtime, ctime, rtime = _update_if_passed(gtime, ctime, rtime)

        return {
            'global': gtime,
            'channel': ctime,
            'room': rtime
        }

    @with_session
    def remove_global_ban(self, user_id: str, session=None) -> None:
        self.env.cache.set_global_ban_timestamp(user_id, '', '', '')
        ban = session.query(Bans)\
            .filter(Bans.user_id == user_id)\
            .filter(Bans.is_global.is_(True)).first()
        if ban is None:
            return
        session.delete(ban)
        session.commit()

    @with_session
    def remove_channel_ban(self, channel_id: str, user_id: str, session=None) -> None:
        self.env.cache.set_channel_ban_timestamp(channel_id, user_id, '', '', '')
        ban = session.query(Bans)\
            .join(Bans.channel)\
            .filter(Channels.uuid == channel_id)\
            .filter(Bans.user_id == user_id)\
            .filter(Bans.is_global.is_(False)).first()
        if ban is None:
            return
        session.delete(ban)
        session.commit()

    @with_session
    def remove_room_ban(self, room_id: str, user_id: str, session=None) -> None:
        self.env.cache.set_room_ban_timestamp(room_id, user_id, '', '', '')
        ban = session.query(Bans)\
            .join(Bans.room)\
            .filter(Rooms.uuid == room_id)\
            .filter(Bans.user_id == user_id)\
            .filter(Bans.is_global.is_(False)).first()
        if ban is None:
            return
        session.delete(ban)
        session.commit()

    def _get_banned_users(self, all_bans, session=None):
        output = dict()
        if all_bans is None or len(all_bans) == 0:
            return output

        should_commit = False
        now = datetime.utcnow()

        for ban in all_bans:
            if now > ban.timestamp:
                session.delete(ban)
                should_commit = True
                continue

            output[ban.user_id] = {
                'name': ban.user_name,
                'duration': ban.duration,
                'reason': ban.reason,
                'timestamp': ban.timestamp.strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
            }

        if should_commit:
            session.commit()
        return output

    @with_session
    def get_banned_users_global(self, session=None) -> dict:
        all_bans = session.query(Bans).filter(Bans.is_global.is_(True)).all()
        return self._get_banned_users(all_bans, session)

    @with_session
    def get_banned_users_for_channel(self, channel_id: str, session=None) -> dict:
        all_bans = session.query(Bans).join(Bans.channel).filter(Channels.uuid == channel_id).all()
        return self._get_banned_users(all_bans, session)

    @with_session
    def get_banned_users_for_room(self, room_id: str, session=None) -> dict:
        all_bans = session.query(Bans).join(Bans.room).filter(Rooms.uuid == room_id).all()
        return self._get_banned_users(all_bans, session)

    def get_banned_users(self):
        @with_session
        def _get_the_bans(session=None):
            output = {
                'global': dict(),
                'channels': dict(),
                'rooms': dict()
            }

            all_bans = session.query(Bans).outerjoin(Bans.room).outerjoin(Bans.channel).all()
            if all_bans is None or len(all_bans) == 0:
                return output

            should_commit = False
            now = datetime.utcnow()

            for ban in all_bans:
                if now > ban.timestamp:
                    session.delete(ban)
                    should_commit = True
                    continue

                if ban.room is not None:
                    if ban.room.uuid not in output['rooms']:
                        output['rooms'][ban.room.uuid] = dict()
                        output['rooms'][ban.room.uuid]['users'] = dict()
                        output['rooms'][ban.room.uuid]['name'] = b64e(ban.room.name)

                    output['rooms'][ban.room.uuid]['users'][ban.user_id] = {
                        'name': b64e(self.get_user_name(ban.user_id)),
                        'duration': ban.duration,
                        'timestamp': ban.timestamp.strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
                    }
                elif ban.channel is not None:
                    if ban.channel.uuid not in output['channels']:
                        output['channels'][ban.channel.uuid] = dict()
                        output['channels'][ban.channel.uuid]['users'] = dict()
                        output['channels'][ban.channel.uuid]['name'] = b64e(ban.channel.name)

                    output['channels'][ban.channel.uuid]['users'][ban.user_id] = {
                        'name': b64e(self.get_user_name(ban.user_id)),
                        'duration': ban.duration,
                        'timestamp': ban.timestamp.strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
                    }
                elif ban.is_global:
                    output['global'][ban.user_id] = {
                        'name': b64e(self.get_user_name(ban.user_id)),
                        'duration': ban.duration,
                        'timestamp': ban.timestamp.strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
                    }

            if should_commit:
                session.commit()
            return output

        return _get_the_bans()

    def kick_user(self, room_id: str, user_id: str) -> None:
        self.leave_room(user_id, room_id)

    def reset_sids_for_user(self, user_id: str) -> None:
        @with_session
        def update_sid(session=None):
            user_sids = session.query(Sids)\
                .filter(Sids.user_uuid == user_id)\
                .all()

            if user_sids is None or len(user_sids) == 0:
                return

            for user_sid in user_sids:
                try:
                    session.delete(user_sid)
                except Exception as e:
                    if user_sid is None:
                        logger.warning('sid already removed after fetching, ignoring: %s' % str(e))
                    else:
                        logger.error('could not remove sid %s for user %s: %s' % (user_sid.sid, user_id, str(e)))
                        self.env.capture_exception(sys.exc_info())

            session.commit()

        if user_id is None or len(user_id.strip()) == 0:
            raise EmptyUserIdException(user_id)
        self.env.cache.reset_sids_for_user(user_id)
        update_sid()

    def remove_sid_for_user(self, user_id: str, sid: str) -> None:
        @with_session
        def update_sid(session=None):
            user_sid = session.query(Sids)\
                .filter(Sids.sid == sid)\
                .first()

            if user_sid is None:
                return

            session.delete(user_sid)
            session.commit()

        @with_session
        def remove_room_sid(session=None):
            room_sids = session.query(RoomSids)\
                .filter(RoomSids.session_id == sid)\
                .all()

            if room_sids is None or len(room_sids) == 0:
                return

            for room_sid in room_sids:
                session.delete(room_sid)
            session.commit()

        self.env.cache.remove_sid_for_user(user_id, sid)

        try:
            update_sid()
        except Exception as e:
            logger.error('could not remove user sid {} for user {} because: {}'.format(sid, user_id, str(e)))
            logger.exception(e)
            self.env.capture_exception(sys.exc_info())

        try:
            remove_room_sid()
        except Exception as e:
            logger.error('could not remove room sid {} for user {} because: {}'.format(sid, user_id, str(e)))
            logger.exception(e)
            self.env.capture_exception(sys.exc_info())

    def add_sid_for_user(self, user_id: str, sid: str) -> None:
        @with_session
        def update_sid(session=None):
            user_sid = session.query(Sids)\
                .filter(Sids.user_uuid == user_id)\
                .filter(Sids.sid == sid)\
                .first()

            if user_sid is not None:
                return

            user_sid = Sids()
            user_sid.user_uuid = user_id
            user_sid.sid = sid
            session.add(user_sid)
            session.commit()

        if user_id is None or len(user_id.strip()) == 0:
            raise EmptyUserIdException(user_id)
        self.env.cache.add_sid_for_user(user_id, sid)
        update_sid()

    def get_user_for_sid(self, sid: str) -> str:
        @with_session
        def _get_user_for_sid(session=None):
            sid_entity = session.query(Sids).filter(Sids.sid == sid).first()
            if sid_entity is None:
                return None
            return sid_entity.user_id

        if sid is None or len(sid.strip()) == 0:
            raise EmptyUserIdException(sid)

        user_id = self.env.cache.get_user_for_sid(sid)
        if user_id is not None and len(sid) > 0:
            return user_id

        user_id = _get_user_for_sid()
        if user_id is not None and len(user_id) > 0:
            self.env.cache.add_sid_for_user(user_id, sid)

        return user_id

    def get_sids_for_user(self, user_id: str) -> list:
        @with_session
        def get_sids(session=None) -> Union[list, None]:
            user_sids = session.query(Sids)\
                .filter(Sids.user_uuid == user_id)\
                .all()

            if user_sids is None:
                return list()
            return [user_sid.sid for user_sid in user_sids if user_sid.sid is not None and len(user_sid.sid) > 0]

        if user_id is None or len(user_id.strip()) == 0:
            raise EmptyUserIdException(user_id)

        all_sids = self.env.cache.get_sids_for_user(user_id)
        if all_sids is None:
            all_sids = list()

        all_sids = [sid for sid in all_sids if sid is not None and len(sid) > 0]
        if len(all_sids) > 0:
            return all_sids.copy()

        all_sids = get_sids()
        self.env.cache.set_sids_for_user(user_id, all_sids)
        return all_sids

    @staticmethod
    def _decode_reason(reason: str=None) -> str:
        if reason is None or len(reason.strip()) == 0:
            return ''
        return b64d(reason)

    @with_session
    def ban_user_global(self, user_id: str, ban_timestamp: str, ban_duration: str, reason: str=None, banner_id: str=None, session=None):
        ban = session.query(Bans)\
            .filter(Bans.user_id == user_id)\
            .filter(Bans.is_global.is_(True)).first()

        username = ''
        try:
            username = self.get_user_name(user_id)
        except NoSuchUserException:
            pass

        self.env.cache.set_global_ban_timestamp(
                user_id, ban_duration, ban_timestamp, self.get_user_name(user_id))

        if ban is None:
            ban = Bans()
            ban.uuid = str(uuid())
            ban.reason = DatabaseRdbms._decode_reason(reason)
            ban.banner_id = banner_id
            ban.user_id = user_id
            ban.user_name = username
            ban.is_global = True

        ban.timestamp = datetime.fromtimestamp(int(ban_timestamp))
        ban.duration = ban_duration

        session.add(ban)
        session.commit()

    def ban_user_room(self, user_id: str, ban_timestamp: str, ban_duration: str, room_id: str, reason: str=None, banner_id: str=None):
        @with_session
        def _ban_user_room(session=None):
            ban = session.query(Bans)\
                .join(Bans.room)\
                .filter(Bans.user_id == user_id)\
                .filter(Rooms.uuid == room_id).first()

            if ban is None:
                room = session.query(Rooms).filter(Rooms.uuid == room_id).first()
                ban = Bans()
                ban.uuid = str(uuid())
                ban.user_id = user_id
                ban.reason = DatabaseRdbms._decode_reason(reason)
                ban.banner_id = banner_id
                ban.room = room
                ban.user_name = username

            ban.timestamp = datetime.fromtimestamp(int(ban_timestamp))
            ban.duration = ban_duration

            try:
                _remove_user_from_room(session)
            except ValueError:
                # happens if the user already left the room
                pass

            session.add(ban)
            session.commit()

        def _remove_user_from_room(session) -> None:
            room = session.query(Rooms)\
                .join(Rooms.users)\
                .filter(Rooms.uuid == room_id)\
                .filter(Users.uuid == user_id)\
                .first()

            user = session.query(Users).filter(Users.uuid == user_id).first()

            if room is not None:
                try:
                    room.users.remove(user)
                except ValueError:
                    # happens if the user already left a room
                    pass
                session.add(room)

        try:
            self.channel_for_room(room_id)
        except NoChannelFoundException:
            raise NoSuchRoomException(room_id)

        username = ''
        try:
            username = self.get_user_name(user_id)
        except NoSuchUserException:
            pass

        self.env.cache.leave_room_for_user(user_id, room_id)
        self.env.cache.set_room_ban_timestamp(
                room_id, user_id, ban_duration, ban_timestamp, self.get_user_name(user_id))

        n_retries = 2
        for i in range(n_retries):
            try:
                _ban_user_room()
                break
            except StaleDataError as e:
                logger.error('stale data when banning user, attempt {}/{}: {}'.format(i, n_retries, str(e)))

    def ban_user_channel(self, user_id: str, ban_timestamp: str, ban_duration: str, channel_id: str, reason: str=None, banner_id: str=None):
        @with_session
        def _ban_user_channel(session=None):
            ban = session.query(Bans)\
                .join(Bans.channel)\
                .filter(Bans.user_id == user_id)\
                .filter(Channels.uuid == channel_id).first()

            if ban is None:
                channel = session.query(Channels).filter(Channels.uuid == channel_id).first()
                ban = Bans()
                ban.uuid = str(uuid())
                ban.reason = DatabaseRdbms._decode_reason(reason)
                ban.banner_id = banner_id
                ban.user_id = user_id
                ban.channel = channel
                ban.user_name = username

            ban.timestamp = datetime.fromtimestamp(int(ban_timestamp))
            ban.duration = ban_duration

            _remove_user_from_rooms_in_channel(session)

            session.add(ban)
            session.commit()

        def _remove_user_from_rooms_in_channel(session) -> None:
            channel = session.query(Channels)\
                .join(Channels.rooms)\
                .join(Rooms.users)\
                .filter(Channels.uuid == channel_id)\
                .filter(Users.uuid == user_id)\
                .first()

            if channel is None:
                return

            if channel.rooms is None or len(channel.rooms) == 0:
                return

            for room in channel.rooms:
                if room.users is None or len(room.users) == 0:
                    continue

                for user in room.users:
                    if user.uuid != user_id:
                        continue

                    try:
                        room.users.remove(user)
                    except ValueError:
                        # happens if the user already left a room
                        pass

                session.add(room)

        if not self.channel_exists(channel_id):
            raise NoSuchChannelException(channel_id)

        username = ''
        try:
            username = self.get_user_name(user_id)
        except NoSuchUserException:
            pass

        self.env.cache.set_channel_ban_timestamp(
                channel_id, user_id, ban_duration, ban_timestamp, self.get_user_name(user_id))

        _ban_user_channel()
