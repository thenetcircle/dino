## RESTful API

### POST /ban

Request contains info on who to ban where. For banning globally:

    {
        "1234": {
            "duration": "24h",
            "reason": "<optional base64 encoded free-text>",
            "admin_id": "<id of user banning (must already exist), or leave empty for default>",
            "type": "global"
        }
    }

Can also ban multiple users at the same time:

    {
        "<user id>": {
            "duration": "24h",
            "type": "global",
            "reason": "<option reason field, base64 encoded>",
            "admin_id": "<optional id of admin user who is banning>"
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

The "reason" field must be base64 encoded. If the "admin_id" field is specified it will be used, if not the default ID
"0" will be used.

Duration is an integer followed by a char for the unit, which can be one of "d", "h", "m", "s" (days, hours, minutes, 
seconds). Negative or 0 durations are not allowed.

When type is set to "global", no target is specified (meaning user is banned from the whole chat server).

Response will be something like the following:

    {
        "<user id>": {
            "status": "OK"
        },
        "<user id>": {
            "status": "FAIL",
            "message": "invalid duration 5k"
        },
        "<user id>": {
            "status": "FAIL",
            "message": "no such user"
        },
        "<user id>" {
            "status": "OK"
        }
    }

### POST /kick

Request contains:

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

The "reason" field must be base64 encoded. If the "admin_id" field is specified it will be used, if not the default ID
"0" will be used.

Response will be something like the following:

    {
        "<user id>": {
            "status": "OK"
        },
        "<user id>": {
            "status": "FAIL",
            "message": "no such user"
        },
        "<user id>" {
            "status": "OK"
        }
    }

### GET /rooms-for-users

Request contains a list of user IDs, e.g.:

    {
        "users": [
            "1234",
            "5678"
        ]
    }

Response would be all rooms each user is currently in (room names and channel names are base64 encoded):

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

### GET /banned

No data required in request.

Response is all banned users, separated by channel, room and globally. Example response:

    {
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

The "timestamp" in the response is the UTC timestamp for when the ban will expire. Names or channels, rooms and users
are all base64 encoded. The dictionary keys for "rooms" are the UUIDs of the rooms, same for channels, while for users
it's their user IDs as keys. The bans for "global" have no separation by room/channel IDs, and no "name" or "users" 
keys.

#### User ID parameter

The `/banned` endpoint supports having a json with user ID's in the request body to only get bans for those users. E.g.:

    curl localhost:5400/banned -d '{"users":["110464"]}' -X GET -H "Content-Type: application/json"

Response would be (slightly different from above example without request body):

    {
        "data": {
            "110464": {
                "channel": {},
                "room": {
                    "1aa3f5f5-ba46-4aca-999a-978c7f2237c7": {
                        "name": "Y29vbCBndXlz",
                        "duration": "15m",
                        "timestamp": "2016-12-14T09:23:00Z"
                    },
                    "675eb2a5-17c6-45e4-bc0f-674241573f22": {
                        "name": "YmFkIGtpZHo=",
                        "duration": "2m",
                        "timestamp": "2016-12-14T09:15:51Z"
                    }
                },
                "global": {}
            }
        },
        "status_code": 200
    }
