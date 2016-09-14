__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

#!/bin/env python
from .server import create_app, socketio

app = create_app(debug=True)

if __name__ == '__main__':
    socketio.run(app)