import time
from pprint import pprint

import eventlet
from flask import Flask
from flask_socketio import SocketIO
from flask import render_template


app = Flask(
    __name__,
    template_folder='templates/'
)

socketio = SocketIO(
    app,
    async_mode='eventlet',
    message_queue='redis://datamining.thenetcircle.lab:6379',
    channel='dino_test_99',
    cors_allowed_origins='*'
)


def online_counter():
    while True:
        try:
            for namespace in socketio.server.manager.get_namespaces():
                pprint(socketio.server.manager.rooms[namespace])

        except KeyError:
            # happens when there's no one online, just ignore
            pass
        except Exception as e:
            print('ERROR: could not count sessions: {}'.format(str(e)))
            time.sleep(1)

        time.sleep(5)


eventlet.spawn_n(online_counter)


@app.route('/ws')
def chat():
    return render_template('index.html')
