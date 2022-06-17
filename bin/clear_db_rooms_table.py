import datetime

import yaml
import os
import psycopg2
import sys
import redis

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
    dbname = config['database']['db']
    dbhost = config['database']['host']
    dbport = config['database']['port']
    dbuser = config['database']['user']
    dbpass = config['database']['password']

    try:
        conn = psycopg2.connect("dbname='%s' user='%s' host='%s' port='%s' password='%s'" % (
            dbname, dbuser, dbhost, dbport, dbpass)
        )
    except:
        raise RuntimeError('could not connect to db')

    cur = conn.cursor()

    # old rooms
    four_days_ago = (datetime.datetime.utcnow() - datetime.timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("delete from room_roles rr where rr.room_id in (select r.id from rooms r left outer join acls a on r.id = a.room_id where r.created < '{}' and a.id is null and r.ephemeral = true limit 10000)".format(four_days_ago))
    cur.execute("delete from rooms r where r.id in (select r.id from rooms r left outer join acls a on r.id = a.room_id where r.created < '{}' and a.id is null and r.ephemeral = true limit 10000)".format(four_days_ago))
    conn.commit()
