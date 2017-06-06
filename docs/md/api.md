## Error Codes

    OK = 200
    UNKNOWN_ERROR = 250

    MISSING_ACTOR_ID = 500
    MISSING_OBJECT_ID = 501
    MISSING_TARGET_ID = 502
    MISSING_OBJECT_URL = 503
    MISSING_TARGET_DISPLAY_NAME = 504
    MISSING_ACTOR_URL = 505
    MISSING_OBJECT_CONTENT = 506
    MISSING_OBJECT = 507
    MISSING_OBJECT_ATTACHMENTS = 508
    MISSING_ATTACHMENT_TYPE = 509
    MISSING_ATTACHMENT_CONTENT = 510

    INVALID_TARGET_TYPE = 600
    INVALID_ACL_TYPE = 601
    INVALID_ACL_ACTION = 602
    INVALID_ACL_VALUE = 603
    INVALID_STATUS = 604
    INVALID_OBJECT_TYPE = 605
    INVALID_BAN_DURATION = 606

    EMPTY_MESSAGE = 700
    NOT_BASE64 = 701
    USER_NOT_IN_ROOM = 702
    USER_IS_BANNED = 703
    ROOM_ALREADY_EXISTS = 704
    NOT_ALLOWED = 705
    VALIDATION_ERROR = 706
    ROOM_FULL = 707

    NO_SUCH_USER = 800
    NO_SUCH_CHANNEL = 801
    NO_SUCH_ROOM = 802
    NO_ADMIN_ROOM_FOUND = 803
    NO_USER_IN_SESSION = 804
    NO_ADMIN_ONLINE = 805

## connect

Responds with event name "gn_connect".

Request contains no data.

Response data if successful:

    {
        "status_code": 200
    }
    
## login

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
                        "content": "superuser,globalmod"
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

* global superuser (globalmod)
* channel owner (owner)
* channel admin (admin)
* room owner (owner)
* room moderator (moderator)

The only difference between global moderator and super user is that the global moderators can't remove static rooms 
(ephemeral set to `false` in room list).

## list_channels

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
                        "displayName": "<channel name>",
                        "url": 8,
                        "objectType": "static",
                        "attachments": [
                            {
                                "summary": "message",
                                "objectType": "membership",
                                "content": "1"
                            }
                        ]
                    },
                    {
                        "id": "<channel UUID>",
                        "displayName": "<channel name>",
                        "url": 20,
                        "objectType": "temporary",
                        "attachments": [
                            {
                                "summary": "join",
                                "objectType": "gender",
                                "content": "f"
                            }
                        ]
                    }
                ]
            },
            "verb": "list"
        }
    }

Each channel has a `url` field, which is the sort order defined in the admin interface, in ascending order (lower `url`
means higher up in the list).

The `objectType` of a channel tells you if this channel only contains static rooms, only temporary rooms or a mix of 
both. Possible values are thus:

* temporary
* static
* mix

If the channel has 0 rooms in it, the objectType will be `mix`.

Attachments for each channel describes the ACLs for that channel.

## list_rooms

Get a list of all rooms for a channel.

Responds with event name `gn_list_rooms`.

Request contains:

    {
        "object": {
            "url": "<channel UUID>"
        },
        "verb": "list"
    }

Response data if successful:

    {
        "status_code": 200,
        "data": {
            "object": {
                "objectType": "rooms",
                "url": "<channel UUID>",
                "attachments": [
                    {
                        "id": "<room UUID>",
                        "displayName": "<room name>",
                        "url": 8,
                        "summary": <number of users in this room (integer)>,
                        "objectType": "static",
                        "content": "moderator,owner",
                        "attachments": [
                            {
                                "summary": "join",
                                "objectType": "gender",
                                "content": "f"
                            }
                        ]
                    },
                    {
                        "id": "<room UUID>",
                        "displayName": "<room name>",
                        "url": 20,
                        "summary": <number of users in this room (integer)>,
                        "objectType": "temporary",
                        "content": "",
                        "attachments": [
                            {
                                "summary": "join",
                                "objectType": "gender",
                                "content": "f"
                            }
                        ]
                    }
                ]
            },
            "verb": "list"
        }
    }

The `url` field for `object` is the `UUID` of the channel that these rooms are for.  

Each room has a `url` field, which is the sort order defined in the admin interface, in ascending order (lower `url`
means higher up in the list).

The `content` field on the attachments describe what kind of role you have for that room. If no roles are set then
content will be empty, otherwise it will be a comma separated list of roles. Possible roles for rooms are:

* moderator
* owner
* globalmod
* superuser

Global roles and roles for channels are returned in the `gn_login` event.

Attachments for each room describes the ACLs for that room.

The `objectType` for each room describes if the room is static or temporary. Static rooms are not removed automatically
when empty, while temporary rooms are removed when the owner leaves (usually only for user created rooms).

## update_user_info

If a user e.g. changes his/her avatar, the change can be broadcasted to users in the same rooms as this user is in. To
e.g. let other users know this user is currently streaming video, the `objectType` `is_streaming` might be used:

    {
        "object": {
            "attachments": [
                {
                    "content": "MA==",
                    "objectType": "is_streaming"
                }
            ],
            "objectType": "userInfo"
        },
        "verb": "update",
        "id": "<server-generated UUID>",
        "published": "<server-generated timestamp, RFC3339 format>"
    }

The `content` of the attachments needs to be base64 encoded.

Updates are saved in redis and thus will be included in the user info returned in [`gn_join`](api.md#join) and 
[`gn_users_in_room`](api.md#join).

Responds with event name `gn_update_user_info`. When the update is sent to other users it will be received as an event
with name [`gn_user_info_updated`](events.md#user-info-updated).

Response data if successful:

    {
        "status_code": 200
    }

Or if missing data, e.g.:

    {
        "status_code": 509,
        "message": "no objectType on attachment for object"
    }

## request_admin

When help is wanted in a room, a user can request for an admin to join and help out. Every channel has an Admin room,
which only admins can see when listing rooms and only admins can join. When a `request_admin` event is sent to the server
it will be delivered to the admin room for that channel and the admins in that room can decide what to do.

Important:

* If no user with the global role `superuser` or `globalmod` is online, the 805 code will be returned ("no admin is 
online").

Responds with event name `gn_request_admin`.

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

If no admin is online, the response will be:

    {
        "status_code": 805,
        "message": "no admin is online"
    }

The `object.content` could be anything, e.g. a base64 encoded json message with link to backend, extra information, a 
reason text etc. 

The event generated to be sent to the admin room is called `gn_admin_requested` (see 
[Events](events.md#admin-presence-requested) for more information).

## leave

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

## users_in_room

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
                        "content": "globalmod,moderator"
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
                        "content": "moderator"
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

The `content` of the user attachment describes the roles this user has in this room, plus any global roles. Examples:

* `globalmod,moderator`
* `moderator`
* `superuser`

If no specific roles, the value will be blank.

## history

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

## status

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

## get_acl

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

## set_acl

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

## create

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
                "displayName": "<name of the new room>",
                "objectType": "temporary"
            },
            "object": {
                "url": "<channel UUID>"
            },
            "verb": "create"
        }
    }
    
The `target.objectType` will always be `temporary` since all rooms created using the API are user created rooms, meaning
they will be automatically removed when the owner leaves.

It is also possible to specify ACLs for a room while creating it, but adding `object.attachments` as in the `set_acl` 
event:

    {
        "target": {
            "displayName": "<name of the new room>"
        },
        "object": {
            "url": "<channel UUID>",
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
        "verb": "create"
    }

## invite

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

## delete

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

## kick

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

## ban

Ban a user from a room for a given amount of time.

Responds with `gn_ban`.

Request contains:

    {
        "target": {
            "id": "<UUID of the room/channel to ban from>",
            "objectType": "<room/channel/global>"
        },
        "object": {
            "id": "<UUID of the user to ban>",
            "summary": "<ban duration, an integer suffixed with one of [d, h, m, s]>",
            "content": "<optional reason field, base64>"
        },
        "verb": "ban"
    }

If banning a used in a room, set objectType to `room` and `target.id` to the uuid of the room. If banning from a channel,
set `objectType` to `channel` and `target.id` to the uuid of the channel. If banning globally, set objectType to `global`
and skip `target.id`.
    
Summary is the duration of the ban. It's a number with a suffix d, h, m or s, meaning days, hours, minutes and seconds.
Only one suffix can be used. E.g.:

* 5m (ban for five minutes),
* 3600s (ban for 3600 seconds, same as 1h),
* 365d (ban for one year).

It's not possible to permanently ban a user, but you can set a very large duration for the same effect. The only
restriction is that the date when the ban ends (`utcnow()+duration`) must be before the year 10000 (date lib restriction).

Response data if successful:

    {
        "status_code": 200
    }

## message

Send a message to a `room` UUID (can be the user UUID or an actual room UUID).

Responds with event name `gn_message`.

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
and the `published` field set to the time the server received the request (in RFC3339 format).

## remove_room

Response with the event name "gn_remove_room".

Request contains:

    {
        "verb": "remove",
        "target": {
            "id": "<room ID>"
        }
    }

Response data if successful:

    {
        "status_code": 200,
        "data": {
            "target": {
                "id": "<room uuid>",
                "displayName": "<room name in base64>",
                "objectType": "room"
            },
            "id": "c42ebf01-3d50-4f27-a345-4ed213be045d",
            "published": "2016-10-07T10:45:34Z",
            "verb": "removed"
        }
    }

## report

No response.

Request contains:

    {
        "verb": "report",
        "object": {
            "id": "<uuid of message>",
            "content": "<the actual message to report, base64>",
            "summary": "<optional reason text, base64>"
        },
        "target": {
            "id": "<user ID to report>"
        }
    }

A report will be sent to both the admin room and as an external event published on the MQ.

## join

Responds with the event name "gn_join".

In the `user` attachments, the `content` fields tells you the room roles that the user has in this room (as a comma
separated value), plus any global roles. Possible roles are:

* superuser,
* globalmod,
* owner,
* moderator,
* admin.

Currently only the `superuser` and `globalmod` role is considered when the `request_admin` api is used.

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
                                "id": "<owner's user ID>",
                                "displayName": "<owner's user name>",
                            },
                            {
                                "id": "<owner's user ID>",
                                "displayName": "<owner's user name>",
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
                                "content": "moderator,owner",
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
                                "id": "<user ID of a user in the room>",
                                "displayName": "<user name of a user in the room>",
                                "content": "superuser",
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
                ]
            },
            "verb": "join",
            "target": {
                "id": "<the room ID that the user joined>"
            }
        }
    }

Attachments for each user contains the user data, e.g. user name, age, city etc.
