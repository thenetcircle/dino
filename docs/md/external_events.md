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
            "id": "197114"
        },
        "target": {
            "displayName": "Y29vbCBndXlz",
            "id": "1aa3f5f5-ba46-4aca-999a-978c7f2237c7",
            "objectType": "room"
        },
        "verb": "kick"
    }

* object.id: ID of the user who got kicked,
* object.displayName: base64 encoded username of the user was kicked,
* target.id: UUID of the room the user was kicked from,
* target.displayName: base64 encoded name of the room.

### User was banned

TODO

### User successfully logged in

TODO

### User disconnected

TODO
