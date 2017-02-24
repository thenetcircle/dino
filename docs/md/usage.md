## Kicking a user

When a user is kicked from a room (from api/web/rest), all messages that user has sent in a room will be deleted.

Every user in the room will receive an event called `gn_user_kicked` with a possible free-text reason field set.

## Banning a user

When a user is banned (from api/web/rest), all messages that user has ever sent in any room will be deleted.

TODO: who receives what event?
