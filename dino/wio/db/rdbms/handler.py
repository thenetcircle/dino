import logging
import sys
import traceback
from datetime import datetime
from functools import wraps
from typing import Union
from uuid import uuid4 as uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from dino.config import ConfigKeys
from dino.config import RoleKeys
from dino.config import UserKeys
from dino.exceptions import EmptyUserIdException
from dino.exceptions import EmptyUserNameException
from dino.exceptions import NoSuchUserException
from dino.exceptions import UserExistsException
from dino.wio.db.rdbms.dbman import Database
from dino.wio.db.rdbms.mock import MockDatabase
from dino.wio.db.rdbms.models import Bans
from dino.wio.db.rdbms.models import GlobalRoles
from dino.wio.db.rdbms.models import Sids
from dino.wio.db.rdbms.models import UserStatus
from dino.wio.db.rdbms.models import Users
from dino.wio.environ import WioEnvironment
from dino.wio.utils import b64d

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


class DatabaseRdbms(object):
    def __init__(self, env: WioEnvironment):
        self.env = env
        if self.env.config.get(ConfigKeys.TESTING, False):
            DatabaseRdbms.db = MockDatabase()
        else:
            DatabaseRdbms.db = Database(env)

    @staticmethod
    def _decode_reason(reason: str=None) -> str:
        if reason is None or len(reason.strip()) == 0:
            return ''
        return b64d(reason)

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

    @with_session
    def ban_user_global(
            self, user_id: str, ban_timestamp: str, ban_duration: str, reason: str=None,
            banner_id: str=None, session=None
    ):
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
            return list()

        all_sids = [sid for sid in all_sids if sid is not None and len(sid) > 0]
        if len(all_sids) > 0:
            return all_sids.copy()

        all_sids = get_sids()
        self.env.cache.set_sids_for_user(user_id, all_sids)
        return all_sids

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

    def get_user_status(self, user_id: str) -> str:
        @with_session
        def _get_user_status(session=None):
            user_status = session.query(UserStatus).filter_by(uuid=user_id).first()
            if user_status is None:
                return UserKeys.STATUS_UNAVAILABLE
            return user_status.status

        status = self.env.cache.get_user_status(user_id)
        if status is not None:
            return status

        status = _get_user_status()
        self.env.cache.set_user_status(user_id, status)
        return status

    def is_super_user(self, user_id: str) -> bool:
        return self._has_global_role(user_id, RoleKeys.SUPER_USER)

    def is_global_moderator(self, user_id: str) -> bool:
        return self._has_global_role(user_id, RoleKeys.GLOBAL_MODERATOR)

    def _has_global_role(self, user_id: str, role: str):
        user_roles = self.get_user_roles(user_id)
        return role in user_roles['global']

    @staticmethod
    def _format_user_roles(g_roles) -> dict:
        return {
            'global': [a for a in g_roles.roles.split(',') if len(a) > 0],
            'channel': dict(),
            'room': dict()
        }

    def get_user_roles(self, user_id: str) -> dict:
        @with_session
        def _roles(session=None) -> dict:
            g_roles = session.query(GlobalRoles).filter(GlobalRoles.user_id == user_id).first()
            return DatabaseRdbms._format_user_roles(g_roles)

        output = self.env.cache.get_user_roles(user_id)
        if output is not None:
            return output

        roles = _roles()
        self.env.cache.set_user_roles(user_id, roles)
        return roles

    def remove_sid_for_user(self, user_id: str, sid: str) -> None:
        @with_session
        def update_sid(session=None):
            user_sid = session.query(Sids)\
                .filter(Sids.user_uuid == user_id)\
                .filter(Sids.sid == sid)\
                .first()

            if user_sid is None:
                return

            session.delete(user_sid)
            session.commit()

        if user_id is None or len(user_id.strip()) == 0:
            raise EmptyUserIdException(user_id)
        self.env.cache.remove_sid_for_user(user_id, sid)
        update_sid()

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

    def set_user_invisible(self, user_id: str) -> None:
        @with_session
        def _set_user_invisible(session=None):
            user_status = session.query(UserStatus).filter(UserStatus.uuid == user_id).first()
            if user_status is None:
                user_status = UserStatus()
                user_status.uuid = user_id

            user_status.status = UserKeys.STATUS_INVISIBLE
            session.add(user_status)
            session.commit()

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
