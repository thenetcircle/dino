## Invisibility

There are multiple ways to change visibility status, either explicitly using the status api, or implicitly using the 
login api:

* REST API [`/status`](rest.md#post-status),
* WS API [`status`](api.md#status),
* WS API [`login`](api.md#login).

When doing an invisible login, the `last_online_at` should not be updated, and the user status in the cache should be 
`3` (invisible, see [the WIO docs](wio.md) for more info). There are however ways to force a different behavior; see 
below.

### Using the REST api for invisible login

To do an invisible login, you can either call the [`REST API /status`](rest.md#post-status) first (before login),
with the `stage` parameter set to `login` (instead of the default `status`), then call this WS API normally to login 
(without `actor.summary: 'login'`). The user will then be invisible _before_ he/she logs in, and the `last_online_at`
will not be updated.

The REST api request would look as follows:

```json
{   
    "id": "<user ID>",
    "status": "invisible",
    "stage": "login"
}   
```

**Note: if `stage` is set to `status` instead of `login`, then `last_online_at` _will_ be updated.**

Next, the WS login request would look as follows:

```json
{
	"verb": "login",
	"actor": {
		"id": "5666",
		"displayName": "Zm9vYmFy",
		"attachments": [{
			"objectType": "token",
			"content": "some-token"
		}]
	}
}
```

Now the user has logged in invisibly. 

**Note: There's no need for `actor.summary: 'login'` here, since we already set the user to invisibly using the rest
API before the user logged in.**

**Note: There's no need to call the WS `status` API now, the user is already invisible.**

### Using the WS api for invisible login

The other option is to set `actor.content` to `invisible` in the WS login request, in which case there's no need to 
call the REST api. The REST api approach is preferred though, since only paying users should be allowed to be invisible, 
so by using the REST api, the community backend can check the membership status before setting a user invisible. When 
using the WS api for this, there's no validation if the user is allowed to be invisible or not, and a user could alter 
the request on client side to circumvent the restriction.

Invisible login using the WS `login` api looks are follows:

```json
{
    "verb": "login",
    "actor": {
		"id": "5666",
		"displayName": "Zm9vYmFy",
        "content": "invisible",
        "attachments": [{
            "objectType": "token",
			"content": "some-token"
        }]
    }
}
```

Now the user has logged in invisibly. 

**Note: There's no need to call the WS `status` API now, the user is already invisible.**

### Changing status to invisible while online

When a user is online, and wants to change his/her status to `invisible`, the WS api `status` can be used.

The request looks as follows:

```json
{
	"verb": "invisible"
}
```

The user will not become invisible, and the `last_online_at` will be updated to this time. A fake `gn_user_disconnected` 
event will be sent to relevant users.

**Note: If the request contains `actor.summary: "login"`, then `last_online_at` _will_ be updated. Thus, when a user is already 
online, don't set the `summary` to `login`; you can leave it out of the request.**
