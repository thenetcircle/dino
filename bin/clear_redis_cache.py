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
import redis
import sys

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
            secrets = yaml.load(open(secrets_path))
        except Exception as e:
            raise RuntimeError("Failed to open secrets configuration {0}: {1}".format(secrets_path, str(e)))
        template = Template(template)
        template = template.safe_substitute(secrets)

    return ast.literal_eval(template)


config = yaml.load(open(dino_home + '/dino.yaml'))[dino_env]
config = load_secrets_file(config)

r_host, r_port = config['cache']['host'].split(':')
r_db = config['cache']['db']
r_server = redis.Redis(host=r_host, port=r_port, db=r_db)
r_server.flushdb()
