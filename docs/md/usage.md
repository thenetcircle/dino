# Create rooms and send messages using the room _name_ instead of _ID_

The client connects and logs in as normal (example user ID `1234`):

```javascript
socket = io.connect(
    'http://' + document.domain + ':' + location.port + '/chat', 
    {transports:['websocket']}
);

socket.on('connect', function() {
    socket.emit('login', {
        verb: 'login',
        actor: {
            id: '1234',
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

## Creating rooms

The REST API `/create` can then be called to create a new room for this user (the user will automatically 
join the room as well). All rooms created using the `POST /create` API will be temporary rooms in the 
default channel, meaning that no channel ID has to be specified when interacting with these rooms:

```sh
curl -X POST -H 'Content-Type: application/json' http://the-host-name:8080/create -d @- << EOF
{
    "user_ids": [
        "1234"
    ],
    "room_name": "dGVzdCByb29tIG5hbWU=",
    "owner_id": "1234",
    "owner_name": "dGVzdCB1c2Vy"
}
EOF
```

The response from the REST API (the `channel_id` is the ID of the default channel for the rooms, 
and is not necessary to know for clients):

```json
{
	"status_code": 200,
	"data": {
		"channel_id": "8d43181a-13e0-4ccc-a64b-ae8e93d36bcd",
		"room_name": "dGVzdCByb29tIG5hbWU=",
		"room_id": "24a65e40-91e3-4ef7-8e15-e01196550482"
	}
}
```

The client will now receive two events over the websocket connection, first one `gn_room_created`:

```json
{
	"actor": {
		"id": "1234",
		"displayName": "dGVzdCB1c2Vy",
		"attachments": [{
			"objectType": "age",
			"content": "MTg="
		}, {"many":"more"}]
	},
	"object": {
		"url": "/ws"
	},
	"target": {
		"id": "8fdef765-ca8d-4f0a-9340-aaaea478d1c5",
		"displayName": "dGVzdCByb29tIG5hbWU=",
		"objectType": "temporary"
	},
	"verb": "create",
	"id": "b2a8ccbf-f768-4cc3-8f6b-39569533f743",
	"published": "2021-03-17T07:17:24Z",
	"provider": {
		"id": "some-provider"
	}
}
```

...then one `gn_user_joined` for the same user (see next section).

## Joining a room

The REST API `POST /join` can now be used for rooms created in the default channel, by 
specifying the `name` of the room instead of the `id` of the room (multiple user IDs 
can be specified to have them all join):

```sh
curl -X POST -H 'Content-Type: application/json' http://the-host-name:8080/join -d @- << EOF
{
    "user_ids": [
        "4321"
    ],
    "room_name": "dGVzdCByb29tIG5hbWU="
}
EOF
```

Response from the REST API:

```json
{
  "status_code": 200
}
```

The user who just joined, and everyone else already in the room, now received a `gn_user_joined` event:

```json
{
	"actor": {
		"id": "4321",
		"displayName": "dGVzdCB1c2Vy",
		"image": {
			"url": "https://some-url/image.jpg"
		},
		"attachments": [{
			"objectType": "age",
			"content": "MTg="
		}, {"many":"more"}],
		"content": "owner"
	},
	"target": {
		"id": "8fdef765-ca8d-4f0a-9340-aaaea478d1c5",
		"displayName": "dGVzdCByb29tIG5hbWU="
	},
	"verb": "join",
	"id": "a791c846-6070-4cac-a591-a87c298bf7a2",
	"published": "2021-03-17T07:17:24Z",
	"provider": {
		"id": "some-provider"
	}
}
```

## Sending message to a room

Using the REST API `POST /send`, we can send messages to the room using the name as 
well (if no user ID is specified, the ID `0` and name `admin` will be used):

```sh
curl -X POST -H 'Content-Type: application/json' http://the-host-name:8080/send -d @- << EOF
{
    "user_id": "1234",
    "user_name": "dGVzdCB1c2Vy",
	"object_type": "room",
	"target_name": "dGVzdCByb29tIG5hbWU=",
	"content": "dGVzdCBjb250ZW50"
}
EOF
```

Response from the REST API:

```json
{
  "status_code": 200
}
```

All users in the room now receive a `message` event:

```json
{
	"object": {
		"content": "dGVzdCBjb250ZW50"
	},
	"provider": {
		"id": "some-provider"
	},
	"target": {
		"objectType": "room",
		"id": "8fdef765-ca8d-4f0a-9340-aaaea478d1c5",
		"url": "/ws",
		"displayName": "dGVzdCByb29tIG5hbWU="
	},
	"actor": {
		"id": "1234",
		"displayName": "dGVzdCB1c2Vy"
	},
	"verb": "send",
	"id": "f29a1633-5de2-4185-9014-26c15af41896",
	"published": "2021-03-17T07:17:40Z"
}
```

Finally, when leaving the room, call the REST API `POST /leave`:

```sh
curl -X POST -H 'Content-Type: application/json' http://the-host-name:8080/leave -d @- << EOF
{
    "user_ids": ["1234"],
	"room_name": "dGVzdCByb29tIG5hbWU="
}
EOF
```

## Kicking a user

TODO

## Banning a user

TODO

## Useful REST APIs that support `room_name` instead of `room_id`

* [POST /create](rest.md#post-create),
* [POST /join](rest.md#post-join),
* [POST /send](rest.md#post-send),
* [POST /leave](rest.md#post-leave),
* [GET /users-in-rooms](rest.md#get-users-in-rooms),
* [GET /count-joins](rest.md#get-count-joins).
