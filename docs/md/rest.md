## GET /acl

Retrieve all ACLs for all non-temporary rooms in all channels.

Example response:

```json
{
	"data": {
		"status": "OK",
		"data": {
			"0efd8a52-7220-4160-88fe-68a15d470d95": [{
				"type": "admin",
				"action": "join",
				"value": ""
			}, {
				"type": "admin",
				"action": "list",
				"value": ""
			}],
			"a81e4726-784a-11e9-bbdd-bbfdfd886868": [{
				"type": "gender",
				"action": "autojoin",
				"value": "m,f"
			}]
		}
	},
	"status_code": 200
}
```

## GET /rooms

Returns a list of all rooms currently existing. Result is cached for 1 minute and might thus not be always up-to-date.

Example response:

```json
{
	"data": [{
		"name": "default",
		"status": "static",
		"id": "2e7d537e-bed5-47c5-a7f6-357075759e5d",
		"channel": "App and Web"
	}, {
		"name": "default1",
		"status": "static",
		"id": "2ddd90ac-1d44-4af5-9c7d-b9191bc35675",
		"channel": "App only"
	}, {
		"name": "default2",
		"status": "temporary",
		"id": "6418dff0-43fc-469a-8f3b-724d3a5dcecf",
		"channel": "Web only"
	}],
	"status_code": 200
}
```

## GET /rooms-acl

Returns a list of all rooms currently existing, that a specific user is 
allowed to join (if a user is not allowed to list a channel, no rooms 
from that channel will be included either). Result is cached for 1 
minute per user id and might thus not be always up-to-date.

Request:

```json
{
	"user_id": "1234"
}
```

Response:

```json
{
    "data": [{
        "status": "static",
        "room_id": "2e7d537e-bed5-47c5-a7f6-357075759e5d",
        "users": 0,
        "room_name": "default",
        "channel_id": "7e1beff2-3d4f-40cc-baa5-f1fd79cc59c0",
        "channel_name": "App and Web"
    }, {
        "status": "static",
        "room_id": "2ddd90ac-1d44-4af5-9c7d-b9191bc35675",
        "users": 0,
        "room_name": "default1",
        "channel_id": "9613fbb5-5eaf-41b1-8480-0b364af04b80",
        "channel_name": "App only"
    }, {
        "status": "static",
        "room_id": "6418dff0-43fc-469a-8f3b-724d3a5dcecf",
        "users": 0,
        "room_name": "default2",
        "channel_id": "a37a51f0-48ed-43ba-9fcb-750ce7ee3fdb",
        "channel_name": "Web only"
    }],
    "status_code": 200
}
```

## POST /acl

Request:

```json
{
	"room_id": "a81e4726-784a-11e9-bbdd-bbfdfd886868",
	"action": "autojoin",
	"acl_type": "gender",
	"acl_value": "age=35,(gender=f|membership=normal)"
}
```

For more examples on the format of the `acl_value` field, see the [ACL](acl.md) section. 

Response:

```json
{
    "data": {
        "status": "OK"
    }, 
    "status_code": 200
}
```

## GET /history

Request contains info on what time slice, target, origin to get history for:

```json
    {
        "from_time": "2016-12-26T08:39:54Z",
        "to_time": "2016-12-28T08:39:54Z",
        "user_id": "124352",
        "room_id": "dedf878e-b25d-4713-8058-20c6f0547c59" # optional
    }
```

Response would be something similar to the following:

```json
    {
        "status_code": 200,
        "data": [{
            "deleted": false,
            "target_name": "YmFkIGtpZHo=",
            "target_id": "675eb2a5-17c6-45e4-bc0f-674241573f22",
            "timestamp": "2017-01-26T04:58:33Z",
            "from_user_name": "YmF0bWFu",
            "message_id": "37db81f2-4e16-4076-b759-8ce1c23a364e",
            "from_user_id": "997110",
            "channel_name": "U2hhbmdoYWk=",
            "body": "aG93IGFyZSB5b3U/",
            "domain": "room",
            "channel_id": "dedf878e-b25d-4713-8058-20c6f0547c59"
        }, {
            "deleted": false,
            "target_name": "YmFkIGtpZHo=",
            "target_id": "675eb2a5-17c6-45e4-bc0f-674241573f22",
            "timestamp": "2017-01-26T04:58:31Z",
            "from_user_name": "YmF0bWFu",
            "message_id": "416d3c60-7197-471c-a706-7dbeca090d11",
            "from_user_id": "997110",
            "channel_name": "U2hhbmdoYWk=",
            "body": "aGVsbG8gdGhlcmU=",
            "domain": "room",
            "channel_id": "dedf878e-b25d-4713-8058-20c6f0547c59"
        }, {
            "deleted": false,
            "target_name": "YmFkIGtpZHo=",
            "target_id": "675eb2a5-17c6-45e4-bc0f-674241573f22",
            "timestamp": "2017-01-26T04:58:16Z",
            "from_user_name": "YmF0bWFu",
            "message_id": "91655457-3712-4c2f-b6f2-c3b0f8be29e5",
            "from_user_id": "997110",
            "channel_name": "U2hhbmdoYWk=",
            "body": "ZmRzYQ==",
            "domain": "room",
            "channel_id": "dedf878e-b25d-4713-8058-20c6f0547c59"
        }]
    }
```

* If neither `from_time` nor `to_time` is specified, the last 7 days will be used as limit,
* If `from_time` is specified but no `to_time`, `to_time` will be `from_time + 7 days`,
* If `to_time` is specified but no `from_time`, `from_time` will be `to_time - 7 days`,
* Either `user_id` or `room_id` is required (both can be specified at the same time),
* `to_time` needs to be after `from_time`.

## POST /heartbeat

For mobile clients, it is sometimes tricky to maintain a constant connection due to fluctuations in network quality 
and data loss. To keep a user in an online state without keeping a connection open, the `/heartbeat` api can be used
instead.

With regular `/heartbeat` calls, a user will not be marked as offline until no more heartbeats are being received.

Multiple user IDs can be batched together into a single `/heartbeat` call.

Request:

```json
[
    "<user ID 1>",
    "<user ID 2>",
    "<user ID n>"
]
```

Response:

```json
{
    "data": {
        "status": "OK"
    }, 
    "status_code": 200
}
```

## POST /full-history

To get all messages sent by a user, call this endpoint with the following data:

```json
{
    "user_id": 1971
    "from_time": "2016-12-26T08:39:54Z", # optional (other needed if this one is specified)
    "to_time": "2016-12-28T08:39:54Z" # optional  (other needed if this one is specified)
}
```

Response looks like this:

```json
{
    "status_code": 200,
    "data": [{
        "message_id": "07bacdd8-42e6-4ace-acee-8d200dd14bfc",
        "from_user_id": "1971",
        "from_user_name": "Um9k=",
        "target_id": "7935a673-da64-4419-818b-e6e0d1864b61",
        "target_name": "TG9iYnk=",
        "body": "eyJtYXNrIjoiMDAiLCJ6IjE2IiwidGV4dCI6ImkgYW0gaW52aXNpYmxlIn0=",
        "domain": "room",
        "channel_id": "84ec4b4f-7482-48ba-83a1-9c9b1c470903",
        "channel_name": "UGVu",
        "timestamp": "2017-05-23T07:32:07Z",
        "deleted": true
    }, {...}]
}
```

## POST /broadcast

Broadcasts a message to everyone on the server. Request needs the `body` and `verb` keys:

```json
{
    "body": "aGkgdGhlcmU=",
    "verb": "broadcast"
}
```

Body needs to be in base64. The verb may be anything, it's up to clients to handle it.

It's also possible to broadcast to only a single room, by specifying a `room_name` (in base64):

```json
{
    "body": "aGkgdGhlcmU=",
    "verb": "broadcast",
    "room_name": "ZGU="
}
```

Event sent to clients:

```json
{
    "content": "aGkgdGhlcmU=",
    "published": "2021-11-22T02:48:38Z",
    "target": {
        "id": "0c643854-4b3d-11ec-b5c8-1325d666ae4c",
        "objectType": "room",
        "displayName": "ZGU="
    },
    "id": "2fd3c08a-62d1-46c3-96d7-b181264f6bcb",
    "verb": "broadcast",
    "actor": {
        "id": "0",
        "displayName": "QWRtaW4="
    },
    "provider": {
        "id": "foobar"
    }
}
```

Note, if no `room_name` is specified, there's no `target` in the above event to clients.

## POST /blacklist

Add a new word to the blacklist. Encode the word in base64 first, then post a request on the following format:

```json
{
    "word": "YmFkd29yZA=="
}
```

Response if OK:

```json
{
    "status_code": 200
}
```

## DELETE /blacklist

Remove a matching word from the blacklist. Encode the word in base64 first, then post a request on the following format:

```json
{
    "word": "YmFkd29yZA=="
}
```

The sent word will be compared lowercase to find  matching lowercased word in the blacklist and remove all words with
and exact match (when both lowercase).

Response if OK:

```json
{
    "status_code": 200
}
```

## POST /set-admin

Set a user as a global moderator.

Request contains user ID and the user's name (in case the user doesn't exist):

```json
{
    "id": "1234",
    "name": "myuser"
}
```

Response if OK:

```json
{
    "status_code": 200
}
```

Or if any errors:

```json
{
    "data": "no name parameter in request", 
    "status_code": 500
}
```

## POST /remove-admin

Remove global moderator status for a user.

Request contains the user's ID only:

```json
{
    "id": "1234"
}
```

Response if OK:

```json
{
    "status_code": 200
}
```

Or if any errors:

```json
{
    "data": "no id parameter in request", 
    "status_code": 500
}
```

## POST /ban

Request contains info on who to ban where. For banning globally:

```json
{
    "1234": {
        "duration": "24h",
        "reason": "<optional base64 encoded free-text>",
        "admin_id": "<id of user banning (must already exist), or leave empty for default>",
        "type": "global",
        "name": "<username in base64, optional>"
    }
}
```

Can also ban multiple users at the same time:

```json
{
    "<user id>": {
        "duration": "24h",
        "type": "global",
        "reason": "<option reason field, base64 encoded>",
        "admin_id": "<optional id of admin user who is banning>",
        "name": "<username in base64, optional>"
    },
    "<user id>": {
        "duration": "10m",
        "target": "<channel uuid>",
        "type": "channel",
        "reason": "<option reason field, base64 encoded>",
        "admin_id": "<optional id of admin user who is banning>"
    },
    "<user id>": {
        "duration": "7d",
        "target": "<room uuid>",
        "type": "room",
        "reason": "<option reason field, base64 encoded>",
        "admin_id": "<optional id of admin user who is banning>"
    }
}
```

For banning as user in a room, you can either use `"target": "<room uuid>"`, `"room_id": "<room_uuid>"` or 
`"room_name": "<room name in base64>"` (if using `room_name`, the room must be in the default channel, which is true
for all rooms created using the `/create` API).

The `name` field must be base64 encoded. The field is also optional and is only used if a ban request is received for 
a user that doesn't exist on the server, e.g. if the user never logged in before it will not exist. If the name is 
not specified, and the user has to be created before banning, the user ID will be set as the name (later when the user 
login the real username will overwrite this).

The `reason` field must be base64 encoded. If the `admin_id` field is specified it will be used, if not the default ID
`0` will be used (the default admin user).

Duration is an integer followed by a char for the unit, which can be one of `d`, `h`, `m`, `s` (days, hours, minutes, 
seconds). Negative or 0 durations are not allowed.

When type is set to `global`, no target is specified (meaning user is banned from the whole chat server).

Response will be something like the following (if failure):

```json
{
    "status": "FAIL",
    "message": "missing target id for user id <user id> and request <the request json>"
}
```

The banning is done async so if any of the provided user bans has invalid parameters the response will only tell you the
first non-valid parameter and for which user ID.

For success the response looks like this:

```json
{
    "status": "OK"
}
```

## POST /kick

Request contains:

```json
{
    "<user id>": {
        "target": "<room uuid>",
        "reason": "<option reason field, base64 encoded>",
        "admin_id": "<optional id of admin user who is kicking>"
    },
    "<user id>": {
        "target": "<room uuid>",
        "reason": "<option reason field, base64 encoded>",
        "admin_id": "<optional id of admin user who is kicking>"
    },
    "<user id>": {
        "target": "<room uuid>",
        "reason": "<option reason field, base64 encoded>",
        "admin_id": "<optional id of admin user who is kicking>"
    }
}
```

The "reason" field must be base64 encoded. If the "admin_id" field is specified it will be used, if not the default ID
"0" will be used.

Response will be something like the following:

```json
{
    "<user id>": {
        "status": "OK"
    },
    "<user id>": {
        "status": "FAIL",
        "message": "no such user"
    },
    "<user id>": {
        "status": "OK"
    }
}
```

## GET /roles

Request contains a list of user IDs, e.g.:

```json
{
    "users": [
        "124352",
        "5678"
    ]
}
```

Response would be something similar to the following:

```json
{
    "data": {
        "124352": {
            "room": {
                "1aa3f5f5-ba46-4aca-999a-978c7f2237c7": [
                    "moderator"
                ],
                "bb0ea500-cd94-11e6-b178-8323deb605bf": [
                    "owner"
                ]
            },
            "channel": {
                "dedf878e-b25d-4713-8058-20c6f0547c59": [
                    "admin", 
                    "owner"
                ]
            },
            "global": [
                "superuser",
                "globalmod"
            ]
        },
        "5678": {
            "room": {},
            "channel": {},
            "global": []
        }
    },
    "status_code": 200
}
```

Possible roles are:

* global superuser (superuser)
* global moderator (globalmod)
* channel owner (owner)
* channel admin (admin)
* room owner (owner)
* room moderator (moderator)

The only difference between global superusers and global moderators is that global superusers can also remove static 
rooms.

## GET /count-joins

Count the cumulative number of joins for a room. Used for counting the number of "views" a live stream has had. The 
count is cached for 8 hours, then fetched from db if requested again.

Using curl:

```sh
curl localhost:7300/count-joins -X GET -H 'Content-Type: application/json' -d @- << EOF
{
    "room_ids": ["2e7d537e-bed5-47c5-a7f6-357075759e5d"]
}
EOF
```

Instead of `room_ids`, we can use `room_names` (base64 encoded) instead (only works for rooms in the default channel, 
e.g. created using `POST /create`):

```sh
curl localhost:7300/count-joins -X GET -H 'Content-Type: application/json' -d @- << EOF
{
    "room_names": ["c29tZSByb29tIG5hbWUK"]
}
EOF
```

If room IDs were used in the request, the keys in the response will also be room IDs, but if room names were used, 
the base64 encoded room name will be the key:

```json
{
  "status_code": 200, 
  "data": {
    "2e7d537e-bed5-47c5-a7f6-357075759e5d": 5,
    "0e88aae3-cb2f-457c-b1be-8e882479bd34": 3290,
    "0c289aaf-3c7b-4290-89bb-e1fa27cd2300": 89
  }
}
```

## GET /users-in-rooms

Request contains a list of room IDs, and an optional `only_count` field (default is `false`), e.g.:

```json
{
    "room_ids": [
        "2ddd90ac-1d44-4af5-9c7d-b9191bc35675",
        "2e7d537e-bed5-47c5-a7f6-357075759e5d"
    ],
    "only_count": false
}
```

Instead of room IDs, we can specify room names (base64 encoded):

```json
{
    "room_names": [
        "c29tZSByb29tIG5hbWUK"
    ]
}
```

Response would be all visible users in the specified rooms, with their user infos attached (`roles` is a 
comma-separated list of roles, e.g. `owner,globalmod`).

If room IDs were used in the request, the keys in the response will also be room IDs, but if room names were used, 
the base64 encoded room name will be the key:

```json
{
	"data": {
		"2ddd90ac-1d44-4af5-9c7d-b9191bc35675": [{
			"id": "898121",
			"info": {
				"membership": "MA==",
				"has_webcam": "eQ==",
				"age": "OTk=",
				"is_streaming": "RmFsc2U=",
				"city": "U2FzZGY=",
				"fake_checked": "eQ==",
				"country": "Y24=",
				"gender": "bQ==",
				"image": "eQ=="
			},
			"roles": "owner",
			"name": "Um9iYnk="
		}],
        "2e7d537e-bed5-47c5-a7f6-357075759e5d": []
	},
	"status_code": 200
}
```

Response if `only_count` is `true`:

```json
{
	"data": {
		"2ddd90ac-1d44-4af5-9c7d-b9191bc35675": 5,
        "2e7d537e-bed5-47c5-a7f6-357075759e5d": 2
	},
	"status_code": 200
}
```

## POST /create

Creates and joins the room (if specified users are online). Rooms created using this API will always be in the default
channel.

Example request:

```json
{
    "user_ids": [
        "1234",
        "5678"
    ],
    "room_name": "<a room name, in base64>",
    "owner_id": "<a user id>",
    "owner_name": "<a user name, in base64>"
}
```

Example response:

```json
{
	"status_code": 200,
	"data": {
		"room_id": "01eafcf0-4ab2-48bb-8ff5-833b056d2727",
		"room_name": "tr19",
		"channel_id": "8d43181a-13e0-4ccc-a64b-ae8e93d36bcd"
	}
}
```

## POST /join

Joins the room (if specified users are online). Only works for rooms in the default channel (e.g. 
rooms created using the `POST /create` API).

If `room_id` is specified, it will be used, otherwise, the `room_name` will be used to lookup the 
correct room in the default channel.

Example request:

```json
{
    "user_ids": [
        "1234",
        "5678"
    ],
    "room_id": "<optional: a room id>",
    "room_name": "<a room name, in base64>"
}
```

Example response:

```json
{
    "status_code": 200,
    "data": {
        "success": 1,
        "failures": 0,
        "errors": []
    }
}
```

If the room does not exist, error code `802` will be returned:

```json
{
    "status_code": 200,
    "data": {
        "success": 0,
        "failures": 1,
        "errors": [{
            "status_code": 802,
            "error": "no room exists with id 01eafcf0-4ab2-48bb-8ff5-833b056d2727 or name <some name>"
        }]
    }
}
```

If the user does not exist (i.e. the user is not online), error code `800` will be returned:

```json
{
    "status_code": 200,
    "data": {
        "success": 0,
        "failures": 1,
        "errors": [{
            "status_code": 800,
            "error": "user not online: 1234"
        }]
    }
}
```

If a user in the `user_ids` list is banned from joining the room (or the channel, or globally), error `703` will be 
returned for that user:

```json
{
    "status_code": 200,
    "data": {
        "success": 0,
        "failures": 1,
        "errors": [{
            "status_code": 703,
            "error": "user 1234 is banned from room/channel/global <some name> for 3601 seconds. Reason: <some reason specified when the user was banned>"
        }]
    }
}
```

## POST /leave

Leaves the room (if specified users are online). Only works for rooms in the default channel (e.g. 
rooms created using the `POST /create` API).

If `room_id` is specified, it will be used, otherwise, the `room_name` will be used to lookup the 
correct room in the default channel.

Example request:

```json
{
    "user_ids": [
        "1234",
        "5678"
    ],
    "room_id": "<optional: a room id>",
    "room_name": "<a room name, in base64>"
}
```

Example response:

```json
{
    "status_code": 200
}
```

## GET /rooms-for-users

Request contains a list of user IDs, e.g.:

```json
{
    "users": [
        "1234",
        "5678"
    ]
}
```

Response would be all rooms each user is currently in (room names and channel names are base64 encoded):

```json
{
    "1234": [{
        "room_id": "efeca2fe-ba93-11e6-bc9a-4f6f56293063",
        "room_name": "b2gsIHNvIHlvdSBhY3R1YWxseSBjaGVja2VkIHdoYXQgaXMgd2FzPw==",
        "channel_id": "fb843140-ba93-11e6-b178-97f0297a6d4d",
        "channel_name": "dG9tIGlzIGEgZnJlbmNoIG1hZG1hbg=="
    }],
    "5678": [{
        "room_id": "ca1dc3b4-ba93-11e6-b835-7f1d961023a1",
        "room_name": "cmVhZCB1cCBvbiBoeXBlcmxvZ2xvZysr",
        "channel_id": "f621fcaa-ba93-11e6-8590-bfe35ff80c03",
        "channel_name": "YSByZWRidWxsIGEgZGF5IGtlZXBzIHRoZSBzYW5kbWFuIGF3YXk="
    }]
}
```

## POST /delete-messages

Used to delete ALL messages for a specific user ID.

Request body looks like this:

```json
{
    "id": "<user ID>"
}
```

Example response:

```json
{
    "status_code": 200, 
    "data": {
        "success": 4, 
        "failed": 0,
        "total": 4
    }
}
```

Or if other kinds of failures:

```json
{
    "status_code": 500, 
    "data": "<error message, e.g. 'no id parameter in request'>"
}
```

## GET /banned

If no request data is sent, the response is all banned users, separated by channel, room and globally. Example response:

```json
{
  "status_code": 200,
  "data": {
    "channels": {},
    "global": {
      "185626": {
        "name": "bHVlbA==",
        "duration": "1h",
        "timestamp": "2016-12-05T03:50:24Z"
      }
    },
    "rooms": {
      "1aa3f5f5-ba46-4aca-999a-978c7f2237c7": {
        "name": "Y29vbCBndXlz",
        "users": {
          "101108": {
            "name": "bHVlbA==",
            "duration": "30m",
            "timestamp": "2016-12-05T03:20:24Z"
          }
        }
      }
    }
  }
}
```

The `timestamp` in the response is the UTC timestamp for when the ban will expire. Names or channels, rooms and users
are all base64 encoded. The dictionary keys for `rooms` are the UUIDs of the rooms, same for channels, while for users
it's their user IDs as keys. The bans for `global` have no separation by room/channel IDs, and no "name" or "users" 
keys.

If `room_id` is specified in the request, the response will only contain bans for that room. If `channel_id` is 
specified, the response will only contain bans for that channel. Example request for bans in a certain room:

```json
{
    "room_id": "1aa3f5f5-ba46-4aca-999a-978c7f2237c7"
}
```

Then the response would be (the key is the user ID; same format if `room_name` is used instead of `room_id`):

```json
{
  "status_code": 200,
  "data": {
    "1234": {
        "name": "<username in base64>",
        "duration": "<seconds left until the ban is lifted>",
        "reason": "<ban reason in base64>",
        "timestamp": "2016-12-05T03:20:24Z"
    },
    "5678": {
        "name": "<username in base64>",
        "duration": "<seconds left until the ban is lifted>",
        "reason": "<ban reason in base64>",
        "timestamp": "2016-12-05T03:20:24Z"
    }
  }
}
```

If only global bans are needed, use the `global` key, and no other keys. Example request:

```json
{
    "global": true
}
```

Response is in the same format as above.

If the room doesn't exist, error `802` is returned:

```json
{
    "status_code": 200,
    "data": {
        "code": 802,
        "message": "no room exists with name <room name>"
    }
}
```

## POST /status

Set the online status or visibility status of a user.

Request contains:


```json
{   
    "id": "<user ID>",
    "status": "<one of online/offline/invisible/visible>",
    "stage": "<one of login/status>"
}   
```

Example response:

```json
{
    "status_code": 200
}
```

## POST /send

If `target_id` is not specified in the request body, but `target_name` is, Dino will try to 
send the message to the room with that name, but it only works for rooms that are in the 
default channel (rooms created using `POST /create` are always in the default channel).

The `target_name` field (if specified), must be base64 encoded.

Request contains:

```json
{   
    "user_id": "<user ID>",
    "user_name": "<username, in base64>",
    "object_type": "<room/private>",
    "target_id": "<user ID to send to or UUID of room to send to>",
    "target_name": "<the name of the user/room to send to, in base64>",
    "content": "<the body to send, in base64>"
}   
```

Example response:

```json
{
    "status_code": 200
}
```

User/room will get something similar to this in a `message` event:

```json
{
    "id": "1d805e18-a773-11e8-a65f-8b33c55c9e1b",
    "published": "2017-01-26T04:58:31Z",
    "actor": {
        "id": "<user ID>",
        "displayName": "<username, in base64>"
    },
    "verb": "send",
    "target": {
        "objectType": "<room/private>",
        "id": "<user ID to send to or UUID of room to send to>",
        "displayName": "<the name of the user/room to send to, in base64>"
    },
    "object": {
        "content": "<the body to send, in base64>"
    }
}
```
