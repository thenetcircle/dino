## RESTful API

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
                "duration": "1h",
                "name": "bHVlbA==",
                "timestamp": "2016-12-05T03:50:24Z"
            }
        },
        "rooms": {
            "1aa3f5f5-ba46-4aca-999a-978c7f2237c7": {
                "name": "Y29vbCBndXlz",
                "users": {
                    "101108": {
                        "duration": "30m",
                        "name": "bHVlbA==",
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
