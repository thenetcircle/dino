## Message deleted

When an admin/mod/etc. deletes a message from a room, everyone on that room will receive an event with the name 
`gn_message_deleted` so they can remove it locally as well.

    {
        "id": "<server-generated UUID>",
        "published": "<server-generated timestamp, RFC3339 format>",
        "object": {
            "id": "<UUID of the message that was deleted>"
        },
        "target": {
            "id": "<UUID of the room the message was deleted in>"
        },
        "verb": "delete",
        "actor": {
            "id": "<ID fo the user who deleted the message>",
            "displayName": "<name of the user, base64>"
        }
    }

## Message received

When user A receives a private message, or a message from a room that user A is in, the event `gn_message` will be sent
to user A with the following content:

    {
        "id": "<server-generated UUID>",
        "published": "<server-generated timestamp, RFC3339 format>",
        "actor": {
            "id": "<UUID of the sender>",
            "displayName": "<name of the sender>"
        },
        "verb": "send",
        "target": {
            "id": "<UUID of the room, or this user's UUID if private msg>",
            "displayName": "<name of the room, or target user name if private msg>",
            "objectType": "<room/private>"
        },
        "object": {
            "content": "<the message body>",
            "displayName": "<the name of the channel, or empty if private msg>",
            "url": "<UUID of the channel for this room, or empty if private msg>"
        }
    }

## User info updated

When a user updates his/her user information (e.g. avatar, is streaming, age etc.), the event `gn_user_info_updated`
will be sent to either all rooms that the user is in, or a specific room that user chose to send to. The event looks 
like this:

    {
        "actor": {
            "id": "997110",
            "displayName": "YmF0bWFu"
        },
        "object": {
            "attachments": [{
                "content": "MA==",
                "objectType": "streaming"
            },{
                "content": "MzU=",
                "objectType": "age"
            }],
            "objectType": "userInfo"
        },
        "verb": "update",
        "id": "<server-generated UUID>",
        "published": "<server-generated timestamp, RFC3339 format>"
    }

The `content` on each attachment is always base64 encoded. The `objectType` tells which field has been updated. Possible
values depends on implementation, but is usually same as what's returned for user info when joining a room (`gn_join`).

## Admin presence requested

When someone requests the presence of an admin in a room all users in the Admin room for that channel will receive an
event called `gn_admin_requested` containing the following:

    {
        "id": "<server-generated UUID>",
        "published": "<server-generated timestamp, RFC3339 format>",
        "actor": {
            "id": "<UUID of user requesting>",
            "displayName": "<name of the user requesting>",,
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
        "verb": "help",
        "object": {
            "content": "<base64 encoded message>"
        },
        "generator": {
            "id": "<UUID of the room the help was requested for>",
            "displayName": "<name of the room>"
        },
        "target": {
            "id": "<UUID of the admin room>",
            "displayName": "<base64 of the admin room name>"
        }
    }

## A room was removed

When a room is removed by an admin/owner an event called `gn_room_removed` will be sent to everyone on the server (to
keep the room list in sync on client side):

    {
        "actor": {
            "id": "<user ID who removed the room>",
            "displayName": "<name of the user who removed the room, in base64>"
        },
        "target": {
            "id": "<room uuid>",
            "displayName": "<room name in base64>",
            "objectType": "room"
        },
        "object": {
            "content": "<an optional reason, in base64>"
        },
        "id": "c42ebf01-3d50-4f27-a345-4ed213be045d",
        "published": "2016-10-07T10:45:34Z",
        "verb": "removed"
    }

## Invitation received

When user B invites user A to join room X, the event `gn_invitation` will be sent to user A with the following content:

    {
        "id": "<server-generated UUID>",
        "published": "<server-generated timestamp, RFC3339 format>",
        "actor": {
            "id": "<UUID of user B>",
            "displayName": "<name of user B>",,
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
        "verb": "invite",
        "object": {
            "url": "<UUID of the channel for room X>",
            "displayName": "<name of the channel for room X>"
        },
        "target": {
            "id": "<UUID of the room>",
            "displayName": "<name of the room>"
        }
    }

## Another user joins the room 

If user A is in room X, and another user B joins room X, the server will send an event called `gn_user_joined` to user A
with the following content:

    {
        "id": "<server-generated UUID>",
        "published": "<server-generated timestamp, RFC3339 format>",
        "actor": {
            "id": "<user B's UUID>",
            "displayName": "<name of user B>",
            "image": {
                "url": "<user B's image url>"
            },
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
        "target": {
            "id": "<uuid of the room>",
            "displayName": "<name of the room>"
        },
        "verb": "join"
    }

## Another user leaves room

When user A is in room X, and another user B leaves room X, the sever will send an event called `gn_user_left` to user A
with the following content:

    {
        "id": "<server-generated UUID>",
        "published": "<server-generated timestamp, RFC3339 format>",
        "actor": {
            "id": "<user B's UUID>",
            "displayName": "<name of user B>",
        },
        "target": {
            "id": "<uuid of the room>",
            "displayName": "<name of the room>"
        },
        "verb": "leave"
    }

## Another user connects

When a user connects (or stops being invisible), the `gn_user_connected` event will be sent.

    {
        "actor": {
            "id": "<user B's UUID>",
            "displayName": "<name of user B>",
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
        "id": "<server-generated UUID>",
        "published": "<server-generated timestamp, RFC3339 format>",
        "verb": "connect"
    }

## Another user disconnects

If user A is in any room that user B is in, and user B disconnects from the chat server, an event called
`gn_user_disconnected` will be sent to user A with the following content:

    {
        "id": "<server-generated UUID>",
        "published": "<server-generated timestamp, RFC3339 format>",
        "actor": {
            "id": "<user B's UUID>",
            "displayName": "<name of user B>",
        },
        "verb": 'disconnect'
    }

## You were banned

If you are banned, either in a room, a channel or globally, you will receive the following event named `gn_banned`:

    {
        "actor": {
            "id": "<ID of the one who banned you>",
            "displayName": "<username of the one who banned you, in base64>"
        },
        "object": {
            "id": "<your user ID>",
            "displayName": "<your username in base64>",
            "summary": "30s",
            "updated": "2017-02-15T09:11:52Z",
            "content": "<the reason for the ban>"
        },
        "target": {
            "id": "<room/channel uuid>",
            "displayName": "<room/channel name, in base64>",
            "objectType": "<room/channel/global>"
        },
        "verb": "ban",
        "id": "<server-generated UUID>",
        "published": "<server-generated timestamp, RFC3339 format>"
    }

* target.id and target.displayName will not be present if target.objectType is "global",
* object.summary is the duration of the ban, e.g. 30s, 2h, 7d etc.,
* object.updated is the timestamp when the ban will expire, in UTC,
* object.content is the reason for the ban, but if no reason is given by the banned, this field will not be present.

## A new room is created

When a new room is created in a channel that user A is in, an event called `gn_room_created` will be sent to user A with
the following content:

    {
        "id": "<server-generated UUID>",
        "published": "<server-generated timestamp, RFC3339 format>",
        "actor": {
            "id": "<UUID of user who created the room>",
            "displayName": "<name of the user who created the room>",,
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
        "object": {
            "url": "<UUID of the channel for this room>"
        },
        "target": {
            "id": "<UUID of the new room>",
            "displayName": "<name of the new room>",
            "objectType": "temporary"
        },
        "verb": "create"
    }
    
The `target.objectType` will always be `temporary` since all rooms created using the API are user created rooms, meaning
they will be automatically removed when the owner leaves.

## A user is kicked from a room

When a user is kicked from a room, an event will be sent to all users in that room (except the kicked user), called 
`gn_user_kicked`, with the following content:

    {
        "id": "<server-generated UUID>",
        "published": "<server-generated timestamp, RFC3339 format>",
        "actor": {
            "id": "<UUID of the kicker>",
            "displayName": "<name of the kicker>",,
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
        "object": {
            "id": "<UUID of the kicked user>",
            "displayName": "<name of the kicked user>",,
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
        "target": {
            "id": "<UUID of the room the user was kicked from>",
            "displayName": "<name of the room the user was kicked from>"
        },
        "verb": "kick"
    }

## A user is banned

TODO: currently the user will be banned, but the "kicked" event will be broadcasted to relevant users. There's currently
no "banned" event for this.
