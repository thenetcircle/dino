External events are activity streams send to the configured external queue (e.g. RabbitMQ).

## User was kicked from a room

Example of activity posted to the external queue:

    {
        "actor": {
            "displayName": "admin",
            "id": "0"
        },
        "object": {
            "displayName": "YXNkZg==",
            "content": "dGhpcyBpcyBhIHJlYXNvbg==",
            "id": "197114"
        },
        "target": {
            "displayName": "Y29vbCBndXlz",
            "id": "1aa3f5f5-ba46-4aca-999a-978c7f2237c7"
        },
        "verb": "kick",
        "id": "<server-generated UUID>",
        "published": "<server-generated timestamp, RFC3339 format>"
    }

* actor.id: ID of the user who kicked, or 0 if from admin interface,
* actor.displayName: name of the user who kicked, or admin if from admin interface,
* object.id: ID of the user who got kicked,
* object.content: base64 encoded "reason" for the kick (optional),
* object.displayName: base64 encoded username of the user was kicked,
* target.id: UUID of the room the user was kicked from,
* target.displayName: base64 encoded name of the room.

## User used a blacklisted word
    
    {
        "actor": {
            "displayName": "YmF0bWFu",
            "id": "997110"
        },
        "object": {
            "content": "aGVsbG8gZnVjayB5b3U=",
            "summary": "ZnVjaw=="
        },
        "target": {
            "displayName": "Y29vbCBndXlz",
            "id": "1aa3f5f5-ba46-4aca-999a-978c7f2237c7"
        },
        "verb": "blacklisted",
        "id": "<server-generated UUID>",
        "published": "<server-generated timestamp, RFC3339 format>"
    }

* target.displayName: name of the room the message was sent in,
* target.id: uuid of the room the message was sent in,
* actor.id: id of the user who sent the message,
* actor.displayName: username of the user who sent the message,
* object.content: the full message that was sent,
* object.summary: the forbidden word that was used.

## User was banned

Example of activity posted to the external queue:

    {
        "actor": {
            "displayName": "admin",
            "id": "0"
        },
        "object": {
            "displayName": "YXNkZg==",
            "id": "1234",
            "summary": "5m",
            "content": "dGhpcyBpcyBhIHJlYXNvbg==",
            "updated": "2016-12-22T07:13:09Z"
        },
        "target": {
            "displayName": "Y29vbCBndXlz",
            "objectType": "room",
            "id": "1aa3f5f5-ba46-4aca-999a-978c7f2237c7"
        },
        "verb": "ban",
        "id": "<server-generated UUID>",
        "published": "<server-generated timestamp, RFC3339 format>"
    }

* actor.id: ID of the user who banned, or 0 if from admin interface,
* actor.displayName: name of the user who banned, or admin if from admin interface,
* object.id: ID of the user who got banned,
* object.displayName: base64 encoded username of the user was banned,
* object.content: base64 encoded "reason" for the ban (optional),
* object.summary: the ban duration,
* object.updated: the datetime when the ban will expire (in UTC),
* target.id: UUID of the room the user was kicked from,
* target.displayName: base64 encoded name of the room,
* target.objectType: one of "room", "channel", "global" (if "global", no displayName or id will be on target)

## Server restarted

When the server REST node starts up it will sent a `restart` event in this format: 

    {
        "verb": "restart",
        "id": "c694ddc3-1b2b-4d43-ae5a-a843c2dce8aa",
        "published": "2017-06-09T07:26:26Z"
    }

## User joins room

When a user joins a room the following activity is published to rabbitmq:

    {
        "object": {
            "attachments": [{
                "content": "MA==",
                "objectType": "membership"
            }, {
                "content": "eQ==",
                "objectType": "image"
            }, {
                "content": "bQ==",
                "objectType": "gender"
            }, {
                "content": "NzA=",
                "objectType": "age"
            }, {
                "content": "c2hhbmdoYWk=",
                "objectType": "city"
            }, {
                "content": "Y24=",
                "objectType": "country"
            }, {
                "content": "eQ==",
                "objectType": "fake_checked"
            }, {
                "content": "eQ==",
                "objectType": "has_webcam"
            }]
        },
        "target": {
            "displayName": "YmFkIGtpZHo=",
            "id": "675eb2a5-17c6-45e4-bc0f-674241573f22"
        },
        "id": "bfa26b43-492f-4ec9-a83e-32e64ba2bc51",
        "actor": {
            "displayName": "YXNvZGZpaGFzZG9maWg=",
            "id": "385280",
            "image": {
                "url": "n"
            }
        },
        "published": "2017-01-04T09:58:37Z",
        "verb": "join"
    }

## User ban was removed

Example of activity when a user's ban was manually removed in the admin interface:

    {
        "actor": {
            "id": "0",
            "displayName": "YWRtaW4="
        },
        "target": {
            "id": "675eb2a5-17c6-45e4-bc0f-674241573f22",
            "displayName": "YmFkIGtpZHo=",
            "objectType": "room"
        },
        "published": "2017-01-03T05:50:11Z",
        "verb": "unban",
        "id": "49b067bb-79fe-48bd-9c03-dc4fd8f60192",
        "object": {
            "id": "124352",
            "displayName": "Zm9vYmFyenoyMw=="
        }
    }

* target.id: room ID or channel ID
* target.objectType: "room", "channel" or "global"
* object.id: ID of the user
* object.displayName: name fo the user

If `target.objectType` is `global` then no `target.id` or `target.displayName` will be included.

## User sends a message to a room/user

Whenever a user sends a message an event will be published to the configured MQ, so another system can analyze activity
level of users. Example activity: 

    {
        "actor": {
            "id": "<user ID">,
            "displayName": "<base64 encoded username>"
        },
        "verb": "send",
        "id": "<server-generated UUID>",
        "published": "<server-generated timestamp, RFC3339 format>"
    }

## User successfully logged in

Example of activity when a user successfully logs in:

    {
        "actor": {
            "id": "<user ID>",
            "displayName": "<base64 encoded username>"
        },
        "verb": "login",
        "id": "<server-generated UUID>",
        "published": "<server-generated timestamp, RFC3339 format>"
    }

## A user was reported for a message he/she sent

A message may be reported in the front-end, and a report will be published to the MQ. The event looks like this:

    {
        "actor": {
            "id": "<user ID that reported the message>",
            "displayName": "<the user name who reported the message>"
        },
        "object": {
            "id": "<uuid of message>",
            "content": "<the actual message to report, base64>",
            "summary": "<optional reason text, base64>"
        },
        "target": {
            "id": "<user ID to report>",
            "displayName": "<the user name of the reported user>"
        },
        "verb": "report",
        "id": "<server-generated UUID>",
        "published": "<server-generated timestamp, RFC3339 format>"
    }

## User disconnected

Example of activity when a user disconnects:

    {
        "actor": {
            "id": "<user ID>",
            "displayName": "<base64 encoded username>"
        },
        "verb": "disconnect",
        "id": "<server-generated UUID>",
        "published": "<server-generated timestamp, RFC3339 format>"
    }

## User becomes invisible

When a user changes the status to become invisible the following event is published to the external queue:

    {
        "id": "<server-generated UUID>",
        "actor": {
            "id": "635328",
            "displayName": "amtia2prYmJrag=="
        },
        "verb": "invisible",
        "published": "<server-generated timestamp, RFC3339 format>"
    }

## User becomes visible after being in visible

When a user changes his status to become visible again after being invisible the following event is sent to the external queue:

    {   
        "id": "<server-generated UUID>",
        "actor": {
            "id": "635328",
            "displayName": "amtia2prYmJrag=="
        },  
        "verb": "online",
        "published": "<server-generated timestamp, RFC3339 format>"
    }   

