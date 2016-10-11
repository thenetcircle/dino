Distributed Notifications
----
[![Build Status](https://travis-ci.org/thenetcircle/dino.svg?branch=master)](https://travis-ci.org/thenetcircle/dino)
[![coverage](https://codecov.io/gh/thenetcircle/dino/branch/master/graph/badge.svg)](https://codecov.io/gh/thenetcircle/dino)
[![Code Climate](https://codeclimate.com/github/thenetcircle/dino/badges/gpa.svg)](https://codeclimate.com/github/thenetcircle/dino)
[![License](https://img.shields.io/github/license/thenetcircle/dino.svg)](LICENSE)


Distributed websocket routing for notifications and chat.

Any number of nodes can be started on different machines or same machine on different port. Flask will handle connection
 routing using either Redis or RabbitMQ as a message queue internally. An nginx reverse proxy needs to sit in-front of
 all these nodes with sticky sessions (ip_hash). Fail-over can be configured in nginx for high availability.
 
Example nginx configuration:

    upstream gridnodes {
        ip_hash;
    
        server some-ip-or-host-1:5210;
        server some-ip-or-host-2:5210;
        server some-ip-or-host-3:5210;
        server some-ip-or-host-4:5210;
        server some-ip-or-host-5:5210;
        server some-ip-or-host-6:5210;
        server some-ip-or-host-7:5210;
        server some-ip-or-host-8:5210;
    }
    
    map $http_upgrade $connection_upgrade {
        default upgrade;
        '' close;
    }
    
    server {
        listen 5200;
    
        location / {
            access_log on;
    
            proxy_pass http://gridnodes;
            proxy_next_upstream error timeout invalid_header http_500;
            proxy_connect_timeout 2;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    
            # WebSocket support (nginx 1.4)
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }

### Future features

* The socket.io flask cluster only acs as the router of events,
* Flask nodes sends events to kafka cluster,
* Kafka cluster enriches streams with a timestamp and sequence id,
* Flask nodes subscribe on certain streams, such as events to be broadcasted (e.g. messages in a chat room),
* For other streams such as updating acls, managing rooms, user info, another application will subscribe and store maybe in a relational db,
* An application will subscribe to the e.g. message streams to store data in cassandra.

### Requirements

Some package requirements (debian/ubuntu):

    $ sudo apt-get install libssl-dev libmysqlclient-dev
    TODO: more requirements...

Requires Python >=3.5. Download and install from source:

    $ wget https://www.python.org/ftp/python/3.5.2/Python-3.5.2.tar.xz
    $ tar -xvf Python-3.5.2.tar.xz
    $ cd Python-3.5.2/
    $ ./configure --prefix=/usr/local --enable-shared LDFLAGS="-Wl,-rpath /usr/local/lib"
    $ make
    $ sudo make altinstall # VERY important to use 'altinstall' instead of 'install'
    $ sudo apt-get install virtualenv
    
TODO: check if docker could be useful: https://www.digitalocean.com/community/tutorials/docker-explained-how-to-containerize-python-web-applications

### Running the application

    $ cd dino/
    $ virtualenv --python=python3.5 env
    $ source env/bin/activate
    (env) $ pip install --upgrade .
    (env) $ ENVIRONMENT=prod gunicorn \
                --error-logfile ~/dino-gunicorn-error.log \
                --log-file ~/dino-gunicorn.log \
                --worker-class eventlet \
                --threads 16 \
                --worker-connections 5000 \
                --workers 1 \
                --bind 0.0.0.0:5210 \
                app:app
                
Add "--reload" during development.

### Basic Protocol

This example is using JavaScript.

First we connect to the server:

    socket = io.connect('http://' + document.domain + ':' + location.port + '/chat');

We'll receive a "connect" event back after successfully connecting. Now we have to send the "login" event to provide the
server with some extra user information and to do authentication:

    socket.on('connect', function() {
        socket.emit('login', {
            verb: 'login',
            actor: {
                id: '<user ID>',
                summary: '<user name>',
                attachments: [
                    {
                        objectType: 'foo',
                        content: 'bar'
                    },
                    {
                        objectType: 'city',
                        content: 'Shanghai'
                    }
                ]
            }
        });
    });
    
All events send to the server will get a response with the same name plus a prefix of "gn_". For example, the login 
event sent above will get the following response, "gn_login", meaning we've successfully authenticated with the server.
Now we can start joining rooms, chatting, sending events etc.

    socket.on('gn_login', function(response) {
        socket.emit('list_rooms', {
            actor: {
                id: '{{ user_id }}'
            },
            verb: 'list'
        });
    });
    
The response from the server will be in JSON format. If no data is expected for the events, only a status code will be
in the response. For example, sending the "join" event to join a room won't return any data, but only the following
(if successful):

    {
        "status_code": 200
    }
    
Failure to execute an event on the server will return code 400:

    {
        "status_code": 400
        "data": "<an error message, always a string>"
    }
    
If an internal server error occurs, code 500 is returned:

    {
        "status_code": 400
        "data": "<an error message, always a string>"
    }
    
For events that contains data in the response, for example when sending the event "list_rooms", we expect to get a list
of rooms in the response. For these events the data part is always a JSON in the ActivityStreams 1.0 format:

    {
        "status_code": 400
        "data": {       
            "object": {
                "objectType": "rooms"
                "attachments": [
                    {
                        "id": "<room ID 1>",
                        "content": "<room name 1>"
                    },
                    {
                        "id": "<room ID 2>",
                        "content": "<room name 2>"
                    },
                    {
                        "id": "<room ID 3>",
                        "content": "<room name 3>"
                    }
                ]
            },
            "verb": "list"
        }
    }

### API

#### connect

Responds with event name "gn_connect".

Request contains no data.

Response data if successful:

    {
        "status_code": 200
    }
    
#### login

Responds with event name "gn_login".

Request contains:

    {
        verb: 'login',
        actor: {
            id: '<user ID>',
            summary: '<user name>',
            attachments: [
                {
                    objectType: 'foo',
                    content: 'bar'
                },
                {
                    objectType: 'city',
                    content: 'Shanghai'
                }
            ]
        }
    }

Response data if successful:

    {
        "status_code": 200
    }

#### message

TODO: sequence number on response

Responds with event name "gn_message".

Request contains:

    {
        actor: {
            id: '<user ID>'
        },
        verb: 'send',
        target: {
            id: '<room ID>'
        },
        object: {
            content: '<the message>',
            objectType: '<group/private>'
        }
    }

Response data if successful:

    {
        "status_code": 200,
        "data": {
            "id": "c42ebf01-3d50-4f27-a345-4ed213be045d",
            "published": "2016-10-07T10:45:34Z",
            "actor": {
                "id": "<user ID>"
            },
            "verb": "send",
            "target": {
                "id": "<room ID>"
            },
            "object": {
                "content": "<the message>",
                "objectType": "<group/private>"
            }
        }
    }
    
The response will send the same ActivityStreams as was in the request, with the addition of a server generated ID (uuid)
and the "published" field set to the time the server received the request (in RFC3339 format).

#### join

Responds with the event name "gn_join".

Request contains:

    {
        actor: {
            id: '<user ID>'
        },
        verb: 'join',
        target: {
            id: '<room ID>'
        }
    }
    
Response data if successful:

    {
        "status_code": 200,
        "data": {
            "object": {
                "objectType": "room",
                "attachments": [
                    {
                        "objectType": "history",
                        "attachments": [
                            {
                                "id": "<message ID>",
                                "content": "<the message content>",
                                "summary": "<user name of the sender>",
                                "published": "<the time it was sent, RFC3339>"
                            },
                            {
                                "id": "<message ID>",
                                "content": "<the message content>",
                                "summary": "<user name of the sender>",
                                "published": "<the time it was sent, RFC3339>"
                            }
                        ]
                    },
                    {
                        "objectType": "owner",
                        "attachments": [
                            {
                                "id": "<owner's user ID>",
                                "content": "<owner's user name>",
                            },
                            {
                                "id": "<owner's user ID>",
                                "content": "<owner's user name>",
                            }
                        ]
                    },
                    {
                        "objectType": "acl",
                        "attachments": [
                            {
                                "objectType": "<ACL type name>",
                                "content": "<ACL value>",
                            },
                            {
                                "objectType": "<ACL type name>",
                                "content": "<ACL value>",
                            }
                        ]
                    },
                    {
                        "objectType": "user",
                        "attachments": [
                            {
                                "id": "<user ID of a user in the room>",
                                "content": "<user name of a user in the room>",
                            },
                            {
                                "id": "<user ID of a user in the room>",
                                "content": "<user name of a user in the room>",
                            }
                        ]
                    },
                ]
            },
            "verb": "join",
            "actor": {
                "id": "<the room ID that the user joined>"
            }
        }
    }
