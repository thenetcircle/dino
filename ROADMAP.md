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
* whisper
    - identical to event "message", but set "verb" to "whisper" instead of "send"
    - whisper logic, how to send to one in group?
    - how to handle two targets? one is the room, the other is the user in the room

0.9.0
---
* rdbms
    - only store messages in cassandra
    - acl, room specs (room names, who's in a room etc.), user status, etc. stored in a rdbms (postgres?)
* cross-group messaging
    - how to handle double actors? one actor is originating room, another is the user in that room
* redefine roles
    - different kinds of roles, e.g. admin, global op, channel op, room op, room mod etc.
    
0.10.0
---
* backend admin interface
    - for fixing things
    - listing users in rooms
    - list rooms in channels
    - list channels
    - create channels
* invite
    - search for online users in chats
    - invite user from other room

0.11.0
---
* stats
    - messages are sent to kafka
    - use target id as topic partition key, to get sequence id per room/user
    - messages first sent to kafka to get timestamped and sequence id
    - online/offline/join/leave/connect/disconnect/kick/etc all sent to kafka for possible analysis
* admins
    - clarify requirements, how to call online admins? they get a private message with a special kind of verb?
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