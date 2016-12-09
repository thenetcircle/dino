# Dino Roadmap

A rough roadmap for possible upcoming features.

0.7.0
---
* one-to-one
* group
* history
    - implementers might only want to store recent messages in redis, for historical messages check own storage
    - full message storage in cassandra (also elasticsearch in the future)
    - message storage in redis with possibility to limit how much is stored
* acls
    - set who can join a room
* external authentication
    - redis for now
* kicking
    - owners can kick
* banning
    - owners can ban from rooms, admins can ban from server (future also channel)
* delete messages
    - admins can delete

0.8.0
---
* hierarchical rooms
    - a room can have a "channel" or "parent"
    - one channel could be a city, and all rooms in that channel are for people in that city
* online status
    - maintain online status tables in redis for other services to use
    - external service for clients to see who of their friends are chatting (read from redis), not in dino
* rdbms
    - only store messages in cassandra
    - acl, room specs (room names, who's in a room etc.), user status, etc. stored in a rdbms (postgres?)
* caching
    - specify which cache to use for some db operations

0.9.0
---
* rdbms support for db module
    - also make use of the cache module for some operations
* redefine roles
    - different kinds of roles, e.g. admin, global op, channel op, room op, room mod etc.
* in-memory cache
    - short ttl in-memory cache for session data so we don't hit db/redis for every single request for validation checks
* cross-group messaging
    - acl for allowing cross-group messaging

0.10.0
---
* last read timestamp for group
    - if online, store timestamp of last read message in group for user
    - if later comes online, client asks for messages since last read timestamp 
* backend admin interface
    - for fixing things
    - listing users in rooms
    - list rooms in channels
    - list channels
    - create channels/roms
    - ban users
    - kick users
    - create admin users manually
    - manage list of admins as user ids
    - change ownership/moderator status for users in channels/rooms
* redo permissions
    - able to set different permissions on rooms/channels based on the api action
    - ACLs on channels for who can create rooms in the channel
    - e.g. some types of users can not join (channel or room), like paying members only etc.
    - ability to choose to filter out rooms list, not displaying rooms that a user is not allowed to join

0.11.0
---
* invite
    - search for online users in chats
    - invite user from other room
* base64 all free-text
    - message body
    - room/channel/user names
* request admin
    - open invitation to room instead of single user
    - the room would be a support room, or admin room
    - predefined room?
* whisper
    - identical to event "message", but set "verb" to "whisper" instead of "send"
    - whisper logic, how to send to one in group?
    - how to handle two targets? one is the room, the other is the user in the room
* unique error codes
    - so tests can know an api call failed for the right reason, and clients can know what went wrong
    - use defined response codes for front-end to be able to display correct error messages
* emit event on socket for kick/ban from ui
    - to be able for clients to do ui updates in response to being kicked/banned 
* rest interface
    - to get information about users in room, online users, etc.

0.12.0
---
* test coverage to 90%+
* stats
    - use statsd for metrics
    - send successful login events and disconnect events to a message queue

0.1X.0
---
* refactoring and cleanup
* invisibility
    - invisible in chats
* backend admin interface
    - show/search message history
* stats
    - messages are sent to kafka
    - use target id as topic partition key, to get sequence id per room/user
    - messages first sent to kafka to get timestamped and sequence id
    - online/offline/join/leave/connect/disconnect/kick/etc all sent to kafka for possible analysis
* blacklist
    - blacklist for room names, since when creating probably have to ask backend if the room exists or not anyway
    - chat messages (future, maybe spam classifier)
* video
    - publisher can kick watcher in group
    - use asl for video rooms so only age-verified users over 18 can watch
* ads
    - clarify requirements (dino listens for ad pushes from some mq?)

FUTURE
---
* kafka stream enrichment
    - nodes send certain types of events to kafka first
    - KafkaStreams enriches incoming message events with id and timestamps, publishes to separate topic
    - nodes listens on the kafka topic containing the enriched events, then routes them to targets
* storage
    - storage not handled by nodes, but by a separate system reading from kafka
* node redesign
    - nodes are very lightweight and robust, only routes events and publish/subscribe to kafka topics
* search
    - full-text search using elasticsearch
    - storage app listening to message topics now also stores a copy in elasticsearch (previously only to cassandra/redis)
