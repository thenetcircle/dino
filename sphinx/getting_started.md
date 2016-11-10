## Getting Started

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
                        objectType: 'token',
                        content: '<auth token>'
                    }
                ]
            }
        });
    });
    
All events send to the server will get a response with the same name plus a prefix of "gn_". For example, the login 
event sent above will get the following response, "gn_login", meaning we've successfully authenticated with the server.
Now we can start joining rooms, chatting, sending events etc.

    socket.on('gn_login', function(response) {
        socket.emit('list_channels', {
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
        "status_code": 500
        "data": "<an error message, always a string>"
    }
    
For events that contains data in the response, for example when sending the event "list_channels", we expect to get a list
of channels in the response. For these events the data part is always a JSON in the ActivityStreams 1.0 format:

    {
        "status_code": 400
        "data": {       
            "object": {
                "objectType": "channels"
                "attachments": [
                    {
                        "id": "<channel ID 1>",
                        "content": "<channel name 1>"
                    },
                    {
                        "id": "<channel ID 2>",
                        "content": "<channel name 2>"
                    },
                    {
                        "id": "<channel ID 3>",
                        "content": "<channel name 3>"
                    }
                ]
            },
            "verb": "list"
        }
    }
