## External Events

External events are activity streams send to the configured external queue (e.g. RabbitMQ).

### User was kicked from a room

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

### User was banned

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

### User sends a message to a room/user

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

### User successfully logged in

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

### User disconnected

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
