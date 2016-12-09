## API

### connect

Responds with event name "gn_connect".

Request contains no data.

Response data if successful:

    {
        "status_code": 200
    }
    
### login

Responds with event name "gn_login".

Request contains:

    {
        verb: "login",
        actor: {
            id: "<user ID>",
            summary: "<user name>",
            attachments: [
                {
                    objectType: "token",
                    content: "<user token>"
                }
            ]
        }
    }

Response data if successful:

    {
        "status_code": 200
    }

### list_channels

Responds with event name "gn_list_channels".

Request contains:

    {
        "verb": "list",
        "target": {
            "objectType": "channel"
        }
    }

Response data if successful:

    {
        "status_code": 200,
        "data": {
            "object": {
                "objectType": "channels",
                "attachments": [
                    {
                        "id": "<channel UUID>",
                        "content": "<channel name>"
                    },
                    {
                        "id": "<channel UUID>",
                        "content": "<channel name>"
                    }
                ]
            },
            "verb": "list"
        }
    }

### list_rooms

Get a list of all rooms for a channel.

Responds with event name "gn_list_rooms".

Request contains:

    {
        "object": {
            "url": "<channel UUID>"
        },
        verb: "list",
        "target": {
            "objectType": "room"
        }
    }

Response data if successful:

    {
        "status_code": 200,
        "data": {
            "object": {
                "objectType": "rooms",
                "attachments": [
                    {
                        "id": "<room UUID>",
                        "content": "<room name>"
                    },
                    {
                        "id": "<room UUID>",
                        "content": "<room name>"
                    }
                ]
            },
            "verb": "list"
        }
    }

### leave

Leave a room.

Responds with event name "gn_leave".

Request contains:

    {
        "target": {
            "id": "<room UUID>"
        },
        verb: "leave"
    }

Response data if successful:

    {
        "status_code": 200
    }

### users_in_room

List all users in a room.

Responds with event name "gn_users_in_room".

Request contains:

    {
        "target": {
            "id": "<room UUID>"
        },
        verb: "list"
    }

Response data if successful:

    {
        "status_code": 200,
        "data": {
            "object": {
                "objectType": "users",
                "attachments": [
                    {
                        "id": "<user UUID>",
                        "content": "<user name>"
                    },
                    {
                        "id": "<user UUID>",
                        "content": "<user name>"
                    }
                ]
            },
            "verb": "list"
        }
    }

### history

TODO: include user UUID as well as user name.

When joining a room the history will be included in the "gn_join" response event. If history is needed for a separate
reason than the "history" event can be used. Can also be used to get history for a private chat with another user, if
"target.id" is set to the user UUID instead of the room UUID.

Responds with event name "gn_history".

Request contains:

    {
        "target": {
            "id": "<room UUID>"
        },
        "updated": "<last read timestamp, if configured in server will return messages since this time>",
        "verb": "list"
    }

Response data if successful:

    {
        "status_code": 200,
        "data": {
            "object": {
                "objectType": "messages",
                "attachments": [
                    {
                        "id": "<message ID>",
                        "content": "<the message content>",
                        "summary": "<user name of the sender>",
                        "published": "<the time it was sent, RFC3339>",
                        "url": "<the user uuid>"
                    },
                    {
                        "id": "<message ID>",
                        "content": "<the message content>",
                        "summary": "<user name of the sender>",
                        "published": "<the time it was sent, RFC3339>",
                        "url": "<the user uuid>"
                    }
                ]
            },
            "target": {
                "id": "<room UUID>"
            },
            "verb": "history"
        }
    }

### status

Change the online status for this user.

Responds with "gn_status".

Request contains:

    {
        "verb": "<one of online/offline/invisible>"
    }

Response data if successful:

    {
        "status_code": 200
    }

### get_acl

Get the permissions (ACL) for a channel or room.

Responds with "gn_get_acl".

Request contains:

    {
        "target": {
            "id": "<room UUID>",
            "objectType": "<room/channel>"
        },
        "verb": "get"
    }

Response data if successful:

    {
        "status_code": 200,
        "data": {
            "target": {
                "id": "<room/channel UUID>",
                "objectType": "<room/channel>"
            },
            "object": {
                "objectType": "acl",
                "attachments": [
                    {
                        "objectType": "<ACL type name>",
                        "content": "<ACL value>",
                        "summary": "<API action, e.g. join/kick/etc>"
                    },
                    {
                        "objectType": "<ACL type name>",
                        "content": "<ACL value>",
                        "summary": "<API action, e.g. join/kick/etc>"
                    }
                ]
            },
            "verb": "get"
        }
    }

### set_acl

Update the permissions of a room/channel. If the "content" is blank, the ACL with that type for the specified action
will be removed. Example "API actions" are "join", "create", "message", "kick". Example "permission types" are "age",
"gender", "membership".

Responds with "gn_set_acl".

Request contains:

    {
        "target": {
            "id": "<room/channel UUID>",
            "objectType": "<room/channel>"
        },
        "object": {
            "objectType": "acl",
            "attachments": [
                {
                    "objectType": "<ACL type name>",
                    "content": "<ACL value>",
                    "summary": "<API action, e.g. join/kick/etc>"
                },
                {
                    "objectType": "<ACL type name>",
                    "content": "<ACL value>",
                    "summary": "<API action, e.g. join/kick/etc>"
                }
            ]
        },
        "verb": "set"
    }

Response data if successful:

    {
        "status_code": 200
    }

### create

Create a new room under a channel. The sender of the event will be set as the first owner of the new room.

Responds with "gn_create".

Request contains:

    {
        "target": {
            "displayName": "<name of the new room>"
        },
        "object": {
            "url": "<channel UUID>"
        },
        "verb": "create"
    }

Response data if successful:

    {
        "status_code": 200,
        "data": {
            "target": {
                "id": "<the generated UUID for this room>",
                "displayName": "<name of the new room>"
            },
            "object": {
                "url": "<channel UUID>"
            },
            "verb": "create"
        }
    }

### invite

Invite another user to a room the current user is already in.

Responds with "gn_invite".

Request contains:

    {
        "target": {
            "id": "<UUID of the user to invite>"
        },
        "actor": {
            "id": "<the user making the invitation>",
            "url": "<the room UUID the invitation is for>"
        },
        "object": {
            "url": "<channel UUID>"
        },
        "verb": "invite"
    }

Response data if successful:

    {
        "status_code": 200
    }

### kick

Kick a user from a room.

Responds with "gn_kick".

Request contains:

    {
        "target": {
            "id": "<UUID of the room to kick from>"
        },
        "object": {
            "id": "<UUID of the user to kick>"
        },
        "verb": "kick"
    }

Response data if successful:

    {
        "status_code": 200
    }

### ban

Ban a user from a room for a given amount of time.

Responds with "gn_ban".

Request contains:
    {
        "target": {
            "id": "<UUID of the room to ban from>"
        },
        "object": {
            "id": "<UUID of the user to ban>",
            "summary": "<ban duration, an integer suffixed with one of [d, h, m, s]>"
        },
        "verb": "kick"
    }

Response data if successful:

    {
        "status_code": 200
    }

### message

Send a message to a "room" UUID (can be the user UUID or an actual room UUID).

Responds with event name "gn_message".

Request contains:

    {
        actor: {
            id: "<user ID>"
        },
        verb: "send",
        target: {
            id: "<room ID>"
        },
        object: {
            content: "<the message>",
            objectType: "<room/private>"
        }
    }

Response data if successful:

    {
        "status_code": 200,
        "data": {
            "id": "c42ebf01-3d50-4f27-a345-4ed213be045d",
            "published": "2016-10-07T10:45:34Z",
            "actor": {
                "id": "<user ID>"
            },
            "verb": "send",
            "target": {
                "id": "<room ID>"
            },
            "object": {
                "content": "<the message>",
                "objectType": "<room/private>"
            }
        }
    }
    
The response will send the same ActivityStreams as was in the request, with the addition of a server generated ID (uuid)
and the "published" field set to the time the server received the request (in RFC3339 format).

### join

Responds with the event name "gn_join".

Request contains:

    {
        actor: {
            id: "<user ID>"
        },
        verb: "join",
        target: {
            id: "<room ID>"
        }
    }
    
Response data if successful:

    {
        "status_code": 200,
        "data": {
            "object": {
                "objectType": "room",
                "attachments": [
                    {
                        "objectType": "history",
                        "attachments": [
                            {
                                "id": "<message ID>",
                                "content": "<the message content>",
                                "summary": "<user name of the sender>",
                                "published": "<the time it was sent, RFC3339>"
                            },
                            {
                                "id": "<message ID>",
                                "content": "<the message content>",
                                "summary": "<user name of the sender>",
                                "published": "<the time it was sent, RFC3339>",
                                "url": "<the user uuid>"
                            }
                        ]
                    },
                    {
                        "objectType": "owner",
                        "attachments": [
                            {
                                "id": "<owner"s user ID>",
                                "content": "<owner"s user name>",
                            },
                            {
                                "id": "<owner"s user ID>",
                                "content": "<owner"s user name>",
                            }
                        ]
                    },
                    {
                        "objectType": "acl",
                        "attachments": [
                            {
                                "objectType": "<ACL type name>",
                                "content": "<ACL value>",
                            },
                            {
                                "objectType": "<ACL type name>",
                                "content": "<ACL value>",
                            }
                        ]
                    },
                    {
                        "objectType": "user",
                        "attachments": [
                            {
                                "id": "<user ID of a user in the room>",
                                "content": "<user name of a user in the room>",
                            },
                            {
                                "id": "<user ID of a user in the room>",
                                "content": "<user name of a user in the room>",
                            }
                        ]
                    },
                ]
            },
            "verb": "join",
            "actor": {
                "id": "<the room ID that the user joined>"
            }
        }
    }
