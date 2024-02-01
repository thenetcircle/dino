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

import yaml
import os
import sys
import redis

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

dino_env = os.getenv('DINO_ENVIRONMENT') or sys.argv[1]
dino_home = os.getenv('DINO_HOME') or sys.argv[2]


if dino_home is None:
    raise RuntimeError('need environment variable DINO_HOME')
if dino_env is None:
    raise RuntimeError('need environment variable DINO_ENVIRONMENT')


def load_secrets_file(config_dict: dict) -> dict:
    from string import Template
    import ast

    secrets_path = dino_home + '/secrets/%s.yaml' % dino_env

    # first substitute environment variables, which holds precedence over the yaml config (if it exists)
    template = Template(str(config_dict))
    template = template.safe_substitute(os.environ)

    if os.path.isfile(secrets_path):
        try:
            secrets = yaml.safe_load(open(secrets_path))
        except Exception as e:
            raise RuntimeError("Failed to open secrets configuration {0}: {1}".format(secrets_path, str(e)))
        template = Template(template)
        template = template.safe_substitute(secrets)

    return ast.literal_eval(template)


config = yaml.safe_load(open(dino_home + '/dino.yaml'))[dino_env]
config = load_secrets_file(config)

dbtype = config['database']['type']

if dbtype == 'redis':
    r_host, r_port = config['database']['host'].split(':')
    r_db = config['database']['db']
    r_server = redis.Redis(host=r_host, port=r_port, db=r_db)
    r_server.flushdb()
else:
    dbdriver = config['database']['driver']
    dbname = config['database']['db']
    dbhost = config['database']['host']
    dbport = config['database']['port']
    dbuser = config['database']['user']
    dbpass = config['database']['password']

    if dbdriver.startswith('postgres'):
        try:
            import psycopg2
            conn = psycopg2.connect("dbname='%s' user='%s' host='%s' port='%s' password='%s'" % (
                dbname, dbuser, dbhost, dbport, dbpass)
            )
        except:
            raise RuntimeError('could not connect to db')

        cur = conn.cursor()
        # clean up old users
        cur.execute("""
        delete from users where id in (
            select u.id from users u 
                left outer join rooms_users_association_table ru 
                on ru.user_id = u.id 
            where ru.user_id is null
        )""")

    elif dbdriver.startswith('mysql'):
        try:
            import MySQLdb
            conn = MySQLdb.connect(passwd=dbpass, db=dbname, user=dbuser, host=dbhost, port=dbport)
        except:
            raise RuntimeError('could not connect to db')

        cur = conn.cursor()
        # clean up old users
        cur.execute("""
        delete from users where id in (
            select uid from (
                select u.id as uid from users u 
                    left outer join rooms_users_association_table ru 
                    on ru.user_id = u.id 
                where ru.user_id is null
            ) as T
        )""")

    else:
        raise RuntimeError('unknown dialect: %s' % dbdriver)

    # clear from being 'online' by being in a room
    cur.execute("""delete from rooms_users_association_table""")
    conn.commit()
