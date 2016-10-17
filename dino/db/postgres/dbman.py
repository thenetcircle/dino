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
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL

from dino import environ
from dino.config import ConfigKeys
from dino.db.postgres import DeclarativeBase

# need to keep these here even if "unused", otherwise create_all(engine) won't find the models
from dino.db.postgres.models import UserStatus
from dino.db.postgres.models import Acls
from dino.db.postgres.models import Rooms
from dino.db.postgres.models import Channels
from dino.db.postgres.models import Roles

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class Database(object):
    def __init__(self):
        """
        Initializes database connection and sessionmaker.
        Creates deals table.
        """
        engine = self.db_connect()
        self.create_tables(engine)
        self.Session = sessionmaker(bind=engine)

    def db_connect(self):
        """
        Performs database connection using database settings from settings.py.
        Returns sqlalchemy engine instance
        """
        config = environ.env.config
        domain = ConfigKeys.DATABASE
        params = {
            'drivername': 'postgres+psycopg2',
            'host': config.get(ConfigKeys.HOST, domain=domain),
            'port': config.get(ConfigKeys.PORT, domain=domain),
            'username': config.get(ConfigKeys.USER, domain=domain),
            'password': config.get(ConfigKeys.PASSWORD, domain=domain),
            'database': config.get(ConfigKeys.DB, domain=domain)
        }
        return create_engine(URL(**params))

    def create_tables(self, engine):
        DeclarativeBase.metadata.create_all(engine)
