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

from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL

from dino.config import ConfigKeys
from dino.db.rdbms import DeclarativeBase

# need to keep these here even if "unused", otherwise create_all(engine) won't find the models
from dino.db.rdbms.models import UserStatus
from dino.db.rdbms.models import Acls
from dino.db.rdbms.models import Rooms
from dino.db.rdbms.models import Channels
from dino.db.rdbms.models import ChannelRoles
from dino.db.rdbms.models import RoomRoles
from dino.db.rdbms.models import Users

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class Database(object):
    def __init__(self, env):
        """
        Initializes database connection and sessionmaker.
        Creates deals table.
        """
        self.env = env
        self.driver = self.env.config.get(ConfigKeys.DRIVER, domain=ConfigKeys.DATABASE, default='postgres+psycopg2')
        self.engine = self.db_connect()
        self.create_tables(self.engine)
        session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(session_factory)

    def db_connect(self):
        """
        Performs database connection using database settings from settings.py.
        Returns sqlalchemy engine instance
        """
        domain = ConfigKeys.DATABASE
        params = {
            'drivername': self.driver,
        }

        # make psycopg2 asynchronous
        if self.driver.startswith('postgres'):
            from psycogreen.gevent import patch_psycopg
            patch_psycopg()
        elif self.driver.startswith('mysql'):
            import MySQLdb
            params['pool_recycle'] = 280
            params['pool_size'] = 100

        host = self.env.config.get(ConfigKeys.HOST, default=None, domain=domain)
        port = self.env.config.get(ConfigKeys.PORT, default=None, domain=domain)
        username = self.env.config.get(ConfigKeys.USER, default=None, domain=domain)
        password = self.env.config.get(ConfigKeys.PASSWORD, default=None, domain=domain)
        database = self.env.config.get(ConfigKeys.DB, default=None, domain=domain)

        if host is not None and host != '':
            params['host'] = host
        if port is not None and port != '':
            params['port'] = port
        if username is not None and username != '':
            params['username'] = username
        if password is not None and password != '':
            params['password'] = password
        if database is not None and database != '':
            params['database'] = database

        return create_engine(URL(**params))

    def truncate(self):
        DeclarativeBase.metadata.drop_all(self.engine)

    def create_tables(self, engine):
        DeclarativeBase.metadata.create_all(engine)
