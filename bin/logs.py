import sys
from subprocess import PIPE
from subprocess import Popen

from flask import Flask
from flask import make_response
from flask_restful import Api
from flask_restful import Resource

app = Flask(__name__)
api = Api(app)
UNIT = sys.argv[4]


class Logs(Resource):
    def __init__(self):
        pass

    def get(self):
        headers = {'Content-Type': 'text/html'}
        p = Popen(["journalctl", "-u", UNIT, "-o", "cat", "-n", "250"], stdout=PIPE)
        lines = "".join([str(line, "utf-8").replace("\n", "<br />") for line in p.stdout])
        return make_response(lines, 200, headers)


api.add_resource(Logs, '/')
