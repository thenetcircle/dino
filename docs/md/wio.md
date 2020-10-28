Online status is kept in redis for users who successfully logs in and keeps their socket connection open.

Four keys are maintained in redis:

* users:online:bitmap
* users:online:set
* users:online:inrooms
* users:multicast
* user:status:USER_ID
* user:online:last:USER_ID

## users:online:bitmap (BITMAP)

The ID of the user is used as the offset in the bitmap. When a user logs in the bit in that offset will be set to 1,
and when the user's socket closes the bit is set to 0.

## users:online:set (SET)

A set containing all the IDs of users who are currently online. When a user logs in the user ID is added to the set, and
when the socket closes the ID is removed from the set.

When a user changes his/her status to invisible his/her ID will also be removed from this set. 

## users:multicast (SET)

Same as `users:online:set`, except that when a user goes invisible the user ID stays in this set. This allows 
multicasting of notifications without showing up as `online`.

## user:status:USER_ID (STRING)

One key for each user containing the status, which is a single character with the following meaning:

* 1: available (online)
* 2: chatting (not currently used)
* 3: invisible
* 4: unavailable (offline)
* 5: unknown

## users:online:inrooms (STRING)

A count of the number of online users who are in rooms. The other online keys includes users who are online but haven't 
joined any rooms, this key does not.

Not updated in real-time, but on a regular interval by a cron job.

## user:online:last:USER_ID (STRING)

A timestamp when the user last went offline. If a user logs in as invisible then logs out as invisible, the timestamp is
NOT changed. If a user is visible and turns invisible, then logs out, the timestamp is set to the time the user went
invisible, not when the user logged out.
