# Create rooms and send messages using the room _name_ instead of _ID_

Useful REST APIs that support `room_name` instead of `room_id`:

* [POST /create](rest.md#post-create),
* [POST /join](rest.md#post-join),
* [POST /send](rest.md#post-send),
* [POST /leave](rest.md#post-leave),
* [POST /ban](rest.md#post-ban),
* [POST /kick](rest.md#post-kick),
* [GET /users-in-rooms](rest.md#get-users-in-rooms),
* [GET /count-joins](rest.md#get-count-joins).

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

```shell
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

```shell
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

```shell
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

## Leaving a room

When leaving the room, call the REST API `POST /leave`:

```sh
curl -X POST -H 'Content-Type: application/json' http://the-host-name:8080/leave -d @- << EOF
{
    "user_ids": ["1234"],
	"room_name": "dGVzdCByb29tIG5hbWU="
}
EOF
```

Response from REST API:

```json
{
    "status_code": 200
}
```

## Banning a user

To ban a user, call the `/ban` API. The request:

```shell
curl -X POST  -H 'Content-Type: application/json' http://the-host-name:8080/ban -d @- << EOF
{
    "921984": {
        "room_name": "YSB0ZXN0IHJvb20gMg==",
        "type": "room",
        "duration": "1s"
    }
}
```

Response from the REST API:

```json
{
	"status_code": 200,
	"data": {
		"status": "OK"
	}
}
```

The banned user will receive three events; `gn_banned` (only the banned user gets this event), 
`gn_user_banned` (all users in the room get this event, including the banned user) and finally 
a `gn_user_kicked` event (all users in the room gets this event as well, including the banned 
user).

The `gn_banned` event (YOU were banned):

```json
{
	"actor": {
		"id": "0",
		"displayName": "YWRtaW4="
	},
	"verb": "ban",
	"object": {
		"id": "921984",
		"displayName": "YWRzZmZhZHNkZmFzYWZkcw==",
		"summary": "1s",
		"updated": "2021-03-19T07:53:25Z"
	},
	"id": "b564c6df-9f6b-4a9d-ab60-dca04f4d9416",
	"published": "2021-03-19T07:53:24Z",
	"target": {
		"objectType": "room",
		"id": "77395763-6d11-4b06-b890-83bfb9c31b89",
		"displayName": "dGVzdCByb29tIDM="
	},
	"provider": {
		"id": "some-provider"
	}
}
```

The `gn_user_banned` event (a user in a room was banned, not necessarily you):

```json
{
	"actor": {
		"id": "0",
		"displayName": "YWRtaW4="
	},
	"object": {
		"id": "921984",
		"displayName": "YWRzZmZhZHNkZmFzYWZkcw=="
	},
	"target": {
		"id": "77395763-6d11-4b06-b890-83bfb9c31b89",
		"displayName": "dGVzdCByb29tIDM="
	},
	"verb": "ban",
	"id": "3fbc29e0-4807-4170-a23a-b41c94b1bd69",
	"published": "2021-03-19T07:53:24Z",
	"provider": {
		"id": "some-provider"
	}
}
```

Finally, the `gn_user_kicked` event, telling people the user has been removed from the room (even the banned user gets this event):

```json
{
	"actor": {
		"id": "0",
		"displayName": "YWRtaW4="
	},
	"object": {
		"id": "921984",
		"displayName": "YWRzZmZhZHNkZmFzYWZkcw=="
	},
	"target": {
		"id": "77395763-6d11-4b06-b890-83bfb9c31b89"
	},
	"verb": "ban",
	"id": "3fbc29e0-4807-4170-a23a-b41c94b1bd69",
	"published": "2021-03-19T07:53:24Z",
	"provider": {
		"id": "some-provider"
	}
}
```

## Kicking a user

Note: instead of using the `/kick` API, the `/ban` api can be used with `duration` set to `1s`.

To kick a user, call the `/ban` API. The request:

```shell
curl -X POST  -H 'Content-Type: application/json' http://the-host-name:8080/kick -d @- << EOF
{
    "921984": {
        "room_name": "YSB0ZXN0IHJvb20gMg=="
    }
}
```

Response from the REST API:

```json
{
	"status_code": 200,
	"data": {
		"921984": "OK"
	}
}
```

Everyone in the room, including the kicked user, will receive the `gn_user_kicked` event:

```json
{
	"actor": {
		"id": "0",
		"displayName": "YWRtaW4="
	},
	"object": {
		"id": "921984",
		"displayName": "YWRzZmZhZHNkZmFzYWZkcw=="
	},
	"target": {
		"id": "683fab21-fcb3-473e-bdab-49ab44600200"
	},
	"verb": "kick",
	"id": "d182efbf-070e-482c-b6b1-929c90b5bb2c",
	"published": "2021-03-19T07:47:16Z",
	"provider": {
		"id": "some-provider"
	}
}
```
