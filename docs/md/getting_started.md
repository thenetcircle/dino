## Quick start

This example is using JavaScript.

First we connect to the server:

    socket = io.connect(
        'http://' + document.domain + ':' + location.port + '/chat', 
        {transports:['websocket']}
    );

We'll receive a `connect` event back after successfully connecting. Now we have to send the `login` event to provide the
server with some extra user information and to do authentication:

    socket.on('connect', function() {
        socket.emit('login', {
            verb: 'login',
            actor: {
                id: '<user ID>',
                attachments: [
                    {
                        objectType: 'token',
                        content: '<auth token>'
                    }
                ]
            }
        });
    });
    
All events sent to the server will get a response with the same name plus a prefix of `gn_`. For example, the login 
event sent above will get the following response, `gn_login`, meaning we've successfully authenticated with the server.
Now we can start joining rooms, chatting, sending events etc.

    socket.on('gn_login', function(response) {
        socket.emit('list_channels', {
            verb: 'list'
        });
    });
    
The response from the server will be in JSON format. If no data is expected for the events, only a status code will be
in the response. For example, sending the `join` event to join a room won't return any data, but only the following
(if successful):

    {
        "status_code": 200
    }
    
Failure to execute an event on the server will return an [error code](api.md#error-codes):

    {
        "status_code": 423,
        "data": "<an error message, always a string>"
    }
    
If an internal server error occurs, code 500 is returned:

    {
        "status_code": 500,
        "data": "<an error message, always a string>"
    }
    
For events that contains data in the response, for example when sending the event `list_channels`, we expect to get a list
of channels in the response. For these events the data part is always a JSON in the ActivityStreams 1.0 format:

    {
        "status_code": 200,
        "data": {       
            "object": {
                "objectType": "channels"
                "attachments": [
                    {
                        "id": "<channel ID 1>",
                        "content": "<channel name 1 in base64>"
                    },
                    {
                        "id": "<channel ID 2>",
                        "content": "<channel name 2 in base64>"
                    },
                    {
                        "id": "<channel ID 3>",
                        "content": "<channel name 3 in base64>"
                    }
                ]
            },
            "verb": "list"
        }
    }

## Encoding

All user names, room names, channel names and chat messages are expected to be base64 encoded unicode strings. All
responses and events originating from the server will also follow this practice, so when listing rooms/channels/users
all names will always be in base64.

## Authentication

If the `redis` authentication method is configured, then when clients send the `login` event to the server, the
supplied `token` and `actor.id` parameter must already exist in Redis. When the server gets the login event it will
check if the token matches the one stored in Redis for this user ID, otherwise it will not authenticate the session.

Therefor, before a client can login, these two values (and any other possible values used for permissions) needs to
first be set in the Redis `hset` with key `user:auth:<user ID>`.

Example:

    $ redis-cli
    127.0.0.1:6379> hset user:auth:1234 token 302fe6be-a72f-11e6-b5fc-330653beb4be
    127.0.0.1:6379> hset user:auth:1234 age 35
    127.0.0.1:6379> hset user:auth:1234 gender m

## Private messaging

When the implementation is for one-to-one messaging and not a group chat, the usage is slightly different. After 
having received the `gn_login` event described above, the user will automatically have joined their own room, 
identified by their `user_id`, and another room identified by their `socket.io` session ID.

When a logged in user wants to send a message to another user (logged in or not), use that user's ID as the
`target.id` of the activity. E.g., if you wish to send a private message to user with ID `6`:

    socket.emit('message', {
        verb: 'send',
        target: {
            id: '6',
            objectType: 'private'
        },
        object: {
            content: '<the message, base64 encoded>'
        }
    });

### Conversation based messaging

Sometimes private messaging should be identified by the unique combination of two user IDs, say `1` and `2`, so
that the history between them can be accesses by both parties. In this case, the client implementation should
generate an identifiable "name" for this combination, and create a room to group these messages in. 

For example, the implementation generates a `thread_id` or `conversation_id` on their side, then call the
[`create`](api.md#create) API with the name set as this generated ID. For example, if the ID `42` is generated 
for the conversation assiciated with the users `A` and `B`:

    socket.emit('create', {
        target: {
            displayName: '42',
            objectType: 'private',
            attatchments: [{
                objectType: 'owners',
                summary: '1,2'
            }]
        },
        verb: 'create'
    }, function(status_code, data, error_msg) {
        // callback method, check create api for format of the data param
    });

The callback method will contain the generated UUID of this room (e,g, `4b90eae8-c82b-11e7-98ba-43d525dbbb29`), 
which should be used when joining, sending message etc. It is the responsibility of the implementer to keep track 
of the room IDs associated with conversations.

To send a message in this `room`, first [`join`](api.md#join) the room (will return the history of this room):

    socket.emit('join', {
        verb: 'join',
        target: {
            id: '4b90eae8-c82b-11e7-98ba-43d525dbbb29'
        }
    }, function(status_code, data, error_msg) {
        // callback method, generated room uuid is data.target.id
    });

Use the [`message`](api.md#message) API to send a message to this room:

    socket.emit('join', {
        verb: 'send',
        target: {
            id: '42',
        },
        object: {
            content: '<the message, base64 encoded>',
        }
    }, function(status_code, data, error_msg) {
        // callback method
    });

If the other user is online, he/she will get the [message received](events.md#message-received) event.

## Java client

Using the [Java socket.io library](https://github.com/socketio/socket.io-client-java), you have to use `http` 
instead of `ws` and `https` instead of `wss` (it's the same thing).

Create your object and use Gson to serialize it to json for a JSONObject (you cannot do a `toString` of the 
obejct, it needs to be a json object):

    Gson gson = new Gson();
    try {
        JSONObject obj = new JSONObject(gson.toJson(o));
        s.emit("login", obj);
    } catch (JSONException e) {
        e.printStackTrace();
    }

## Delivery acknowledgment

All APIs will respond with a (status code, error message) tuple. These should be be 
retrieved in the callback defined on the client side. If there was no error, the  
second argument will be nil. Examples of callbacks on client side in JavaScript:

    socket.emit('message', '<omitted json message>', function(status_code, error_message) {
        console.log('Callback called with status_code:', status_code);
        console.log('Callback called with error_message:', error_message);
    });  

## Limited sessions

The session handler can be configured to either allow only one simultaneous connection per user or
an unlimited amount. If only one session is allowed, then whenever a new session by the same user
is started, the previous connection will be disconnected.

