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
            "id": "<user ID>",
            "displayName": "<user name>",
            "attachments": [
                {
                    "objectType": "token",
                    "content": "<user token>"
                }
            ]
        }
    }

Response data if successful:

    {
        "status_code": 200,
        "data": {
            "id": "<server-generated UUID>",
            "published": "<server-generated timestamp, RFC3339 format>",
            "actor": {
                "id": user_id,
                "displayName": b64e(user_name),
                "attachments": [
                    {
                        "objectType": "room_role",
                        "id": "<room UUID>",
                        "content": "moderator,owner"
                    },
                    {
                        "objectType": "room_role",
                        "id": "<room UUID>",
                        "content": "owner"
                    },
                    {
                        "objectType": "channel_role",
                        "id": "<channel UUID>",
                        "content": "admin,owner"
                    },
                    {
                        "objectType": "global_roles",
                        "content": "superuser"
                    }
                ]
            },
            "verb": "login"
        }
    }
    
For the user roles, there will be an ID on the attached object if the role is for a channel or for a room. If it's a
global role there will be no ID on the object. Roles are comma separated if more than one role for a 
room/channel/global.

Possible roles are:

* global superuser
* channel owner
* channel admin
* room owner
* room moderator

### list_channels

Responds with event name "gn_list_channels".

Request contains:

    {
        "verb": "list"
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
                        "displayName": "<channel name>"
                    },
                    {
                        "id": "<channel UUID>",
                        "displayName": "<channel name>"
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
        verb: "list"
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
                        "displayName": "<room name>",
                        "summary": <number of users in this room (integer)>,
                        "content": "moderator,owner"
                    },
                    {
                        "id": "<room UUID>",
                        "displayName": "<room name>",
                        "summary": <number of users in this room (integer)>,
                        "content": ""
                    }
                ]
            },
            "verb": "list"
        }
    }

The "content" field on the attachments describe what kind of role you have for that room. If no roles are set then
content will be empty, otherwise it will be a comma separated list of roles. Possible roles for rooms are:

* moderator
* owner

Global roles and roles for channels are returned in the `gn_login` event.

### request_admin

When help is wanted in a room, a user can request for an admin to join and help out. Every channel has an Admin room,
which only admins can see when listing rooms and only admins can join. When a request_admin event is sent to the server
it will be delivered to the admin room for that channel and the admins in that room can decide what to do.

Responds with event name "gn_request_admin".

Request contains:

    {
        "target": {
            "id": "<room UUID to request help for>"
        },
        "object": {
            "content": "<base64 encoded message that will be delivered to the admin room>"
        },
        "verb": "help"
    }

Response data if successful:

    {
        "status_code": 200
    }

The "object.content" could be anything, e.g. a base64 encoded json message with link to backend, extra information, a 
reason text etc. 

The event generated to be sent to the admin room is called "gn_admin_requested" (see 
[Events](docs/md/events.md#gn_admin_requested) for more information).

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
                        "displayName": "<user name>",
                        "attachments": [
                            {
                                "content": "NDA=",
                                "objectType": "age"
                            },
                            {
                                "content": "aHR0cDovL3NvbWUtdXJsLnRsZC9mb28uanBn",
                                "objectType": "avatar"
                            }
                        ]
                    },
                    {
                        "id": "<user UUID>",
                        "displayName": "<user name>",
                        "attachments": [
                            {
                                "content": "NDA=",
                                "objectType": "age"
                            },
                            {
                                "content": "aHR0cDovL3NvbWUtdXJsLnRsZC9mb28uanBn",
                                "objectType": "avatar"
                            }
                        ]
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
                        "author": {
                            "id": "<the user id of the sender>",
                            "displayName": "<the user name of the sender>"
                        },
                        "id": "<message ID>",
                        "content": "<the message content>",
                        "published": "<the time it was sent, RFC3339>"
                    },
                    {
                        "author": {
                            "id": "<the user id of the sender>",
                            "displayName": "<the user name of the sender>"
                        },
                        "id": "<message ID>",
                        "content": "<the message content>",
                        "published": "<the time it was sent, RFC3339>"
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
            "url": "<the room UUID the invitation is for>"
        },
        "verb": "invite"
    }

Response data if successful:

    {
        "status_code": 200
    }

### delete

Delete a message from a room (needs to be superuser, admin for channel, owner of channel, moderator for room or owner 
of room).

Responds with "gn_delete".

Request contains:

    {
        "target": {
            "id": "<UUID of the room to delete from>"
        },
        "object": {
            "id": "<UUID of the message to delete>"
        },
        "verb": "delete"
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
            "id": "<UUID of the room/channel to ban from>",
            "objectType": "<room/channel/global>"
        },
        "object": {
            "id": "<UUID of the user to ban>",
            "summary": "<ban duration, an integer suffixed with one of [d, h, m, s]>"
        },
        "verb": "kick"
    }

If banning a used in a room, set objectType to "room" and target.id to the uuid of the room. If banning from a channel,
set objectType to "channel" and target.id to the uuid of the channel. If banning globally, set objectType to "global"
and skip target.id.
    
Summary is the duration of the ban. It's a number with a suffix d, h, m or s, meaning days, hours, minutes and seconds.
Only one suffix can be used. E.g.:

* 5m (ban for five minutes),
* 3600s (ban for 3600 seconds, same as 1h),
* 365d (ban for one year).

It's not possible to permanently ban a user, but you can set a very large duration for the same effect. The only
restriction is that the date when the ban ends (utcnow()+duration) must be before the year 10000 (date lib restriction).

Response data if successful:

    {
        "status_code": 200
    }

### message

Send a message to a "room" UUID (can be the user UUID or an actual room UUID).

Responds with event name "gn_message".

Request contains:

    {
        verb: "send",
        target: {
            id: "<room/user ID>",
            objectType: "<room/private>"
        },
        object: {
            content: "<the message, base64 encoded>",
        }
    }

Response data if successful:

    {
        "status_code": 200,
        "data": {
            "id": "c42ebf01-3d50-4f27-a345-4ed213be045d",
            "published": "2016-10-07T10:45:34Z",
            "actor": {
                "id": "<your user ID>",
                "displayName": "<your user name>"
            },
            "verb": "send",
            "target": {
                "id": "<room ID>",
                "displayName": "<room name>"
            },
            "object": {
                "content": "<the message>",
                "displayName": "<the channel name>",
                "url": "<the channel id>",
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
        "verb": "join",
        "target": {
            "id": "<room ID>"
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
                                "author": {
                                    "id": "<the user id of the sender>",
                                    "displayName": "<the user name of the sender>"
                                },
                                "id": "<message ID>",
                                "content": "<the message content>",
                                "published": "<the time it was sent, RFC3339>"
                            },
                            {
                                "author": {
                                    "id": "<the user id of the sender>",
                                    "displayName": "<the user name of the sender>"
                                },
                                "id": "<message ID>",
                                "content": "<the message content>",
                                "published": "<the time it was sent, RFC3339>"
                            }
                        ]
                    },
                    {
                        "objectType": "owner",
                        "attachments": [
                            {
                                "id": "<owner"s user ID>",
                                "displayName": "<owner"s user name>",
                            },
                            {
                                "id": "<owner"s user ID>",
                                "displayName": "<owner"s user name>",
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
                                "displayName": "<user name of a user in the room>",
                            },
                            {
                                "id": "<user ID of a user in the room>",
                                "displayName": "<user name of a user in the room>",
                            }
                        ]
                    },
                ]
            },
            "verb": "join",
            "target": {
                "id": "<the room ID that the user joined>"
            }
        }
    }
