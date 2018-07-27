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
from functools import wraps

from zope.interface import implementer

from dino.config import ConfigKeys
from dino.db import IDatabase
from dino.db.rdbms.dbman import Database
from dino.db.rdbms.handler import DatabaseRdbms
from dino.db.rdbms.mock import MockDatabase
from dino.environ import GNEnvironment
from dino.wio.environ import WioEnvironment

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


class DatabaseRdbms2(object):
    def __init__(self, env: WioEnvironment):
        self.env = env
        if self.env.config.get(ConfigKeys.TESTING, False):
            DatabaseRdbms2.db = MockDatabase()
        else:
            DatabaseRdbms2.db = Database(env)


@implementer(IDatabase)
class DatabaseRdbmsWio(DatabaseRdbms):
    def __init__(self, env: GNEnvironment):
        super().__init__(env)
