## Quick start

This example is using JavaScript.

First we connect to the server:

```javascript
socket = io.connect(
    'http://' + document.domain + ':' + location.port + '/chat', 
    {transports:['websocket']}
);
```

We'll receive a `connect` event back after successfully connecting. Now we have to send the `login` event to provide the
server with some extra user information and to do authentication:

```javascript
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
```

All events sent to the server will get a response with the same name plus a prefix of `gn_`. For example, the login 
event sent above will get the following response, `gn_login`, meaning we've successfully authenticated with the server.
Now we can start joining rooms, chatting, sending events etc.

```javascript
socket.on('gn_login', function(response) {
    socket.emit('list_channels', {
        verb: 'list'
    });
});
```

The response from the server will be in JSON format. If no data is expected for the events, only a status code will be
in the response. For example, sending the `join` event to join a room won't return any data, but only the following
(if successful):

```json
{
    "status_code": 200
}
```

Failure to execute an event on the server will return an [error code](api.md#error-codes):

```json
{
    "status_code": 423,
    "data": "<an error message, always a string>"
}
```

If an internal server error occurs, code 500 is returned:

```json
{
    "status_code": 500,
    "data": "<an error message, always a string>"
}
```

The format of the response can be configured, e.g. to return key "error" for error messages and use "data" only for json
data.

For events that contains data in the response, for example when sending the event `list_channels`, we expect to get a list
of channels in the response. For these events the data part is always a JSON in the ActivityStreams 1.0 format:

```javascript
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
```

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

Sometimes private messaging should be identified by the unique combination of two user IDs, say `1` and `2`, so
that the history between them can be accesses by both parties. In this case, the client implementation should
generate an identifiable "name" for this combination, and create a room to group these messages in. 

For example, the implementer generates a `thread_id` or `conversation_id` on their side, then call the
[`create`](api.md#create) API with the name set as this generated ID. For example, if the ID `42` is generated 
for the conversation assiciated with the users `1` and `2`:

```javascript
socket.emit('create', {
    verb: 'create'
    object: {
        url: '<channel uuid>'
    },
    target: {
        displayName: '42',
        objectType: 'private',
        attachments: [{
            objectType: 'owners',
            summary: '1,2'
        }]
    }
}, function(status_code, data, error_msg) {
    // callback method, check create api for format of the data param
});
```

The callback method will contain the generated UUID of this room (e,g, `4b90eae8-c82b-11e7-98ba-43d525dbbb29`), 
which should be used when joining, sending message etc. It is the responsibility of the implementer to keep track 
of the room IDs associated with conversations.

All users specied as the "owners" will receive the [`gn_room_created`](events.md#a-new-room-is-created) event if 
they are online, otherwise they would get it as history later.

To send a message in this `room`, first [`join`](api.md#join) the room (will return the history of this room):

```javascript
socket.emit('join', {
    verb: 'join',
    target: {
        id: '4b90eae8-c82b-11e7-98ba-43d525dbbb29'
    }
}, function(status_code, data, error_msg) {
    // callback method
});
```

Alternatively, a room can be joined by the `display_name` instead of by `id`, in case that the UUID is not known
on the client side a the time of joining. If multiple rooms exists with the same `display_name`, the `join` event 
will fail with the [error code 715](api.md#error-codes), though in reality that should not happen unless the
uniqueness of room names per channel during creation has been disabled. 

Example of joining using `display_name`:

```javascript
socket.emit('join', {
    verb: 'join',
    target: {
        display_name: '42'
    }   
}, function(status_code, data, error_msg) {
    // callback method, generated room uuid is data.target.id
});
```

Use the [`message`](api.md#message) API to send a message to this room:

```javascript
socket.emit('message', {
    verb: 'send',
    target: {
        id: '4b90eae8-c82b-11e7-98ba-43d525dbbb29',
    },
    object: {
        content: '<the message, base64 encoded>',
    }
}, function(status_code, data, error_msg) {
    // callback method
});
```

If the other user is online, he/she will get the [message received](events.md#message-received) event.

## Java client

Using the [Java socket.io library](https://github.com/socketio/socket.io-client-java), you have to use `http` 
instead of `ws` and `https` instead of `wss` (it's the same thing).

Create your object and use Gson to serialize it to json for a JSONObject (you cannot do a `toString` of the 
obejct, it needs to be a json object):

```java
Gson gson = new Gson();
try {
    JSONObject obj = new JSONObject(gson.toJson(o));
    s.emit("login", obj);
} catch (JSONException e) {
    e.printStackTrace();
}
```

## Delivery acknowledgment

All APIs will invoke the callback (if specified) with a `status_code` and possibly `error_message` (if any 
errors). These should be be retrieved in the callback defined on the client side. If there was no error, the  
second argument will be nil. Examples of callbacks on client side in JavaScript:

```javascript
socket.emit('message', '<omitted json message>', function(status_code, error_msg) {
    // do something
});  
```

Messages should also be awknowledged by the client when [received](api.md#received). An awknowledgement can also 
be sent by the client when a messages as been [read](api.md#read), to let other clients know if the message has 
been seen or not.

Unawknowledged (no received ack sent by client) messages will in future version be redelivered since it might
indicate a loss during transmission.

Example of sending acknowledgement of received message as well as listening for the `OK` server response to
the ack:

```javascript
socket.on('gn_message', function(response) {
    if (response.status_code !== 200) {
        // handle error some way
        return;
    }

    // acknowledge that we got the message
    socket.emit('received', {
        verb: 'receive',
        target: {
            id: room_id
        },
        object: {
            attachments: [{
                // response.data.id is the generated uuid of the message, see api docs
                id: response.data.id
            }]
        }
    }, function(status_code, error_msg) {
        // server "acks our ack"
        console.log('callback for received api: ' + status_code)
    });

    // finally handle the message
    handle_message(data);
});
```

## Limited sessions

The session handler can be configured to either allow only one simultaneous connection per user or
an unlimited amount. If only one session is allowed, then whenever a new session by the same user
is started, the previous connection will be disconnected.

