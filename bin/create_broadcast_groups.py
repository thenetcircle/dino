from uuid import uuid4 as uuid
import sys

from dino.environ import env
from dino.config import ApiActions
from dino.db.manager import AclManager

print("\n"*10)

if len(sys.argv) < 2 or sys.argv[1] not in {"list", "add"}:
    print("usage: DINO_ENVIRONMENT=<env> ./create_broadcast_groups.py list")
    print("usage: DINO_ENVIRONMENT=<env> ./create_broadcast_groups.py add <name> <acl_value>")
    print("\n"*10)
    sys.exit(1)


acl_manager = AclManager(env)


if sys.argv[1] == "list":
    room_acls = env.db.get_room_acls_for_action(ApiActions.AUTOJOIN)

    for room_id, acls in room_acls.items():
        # sometimes room_id is None, if no autojoin rooms exist
        if room_id is None or len(room_id.strip()) == 0:
            continue

        # acls = acl_manager.get_acls_room(room_id, encode_result=False)

        print("{}: {}".format(room_id, env.db.get_room_name(room_id)))
        print("type \t value".expandtabs(20))
        print("---- \t -----".expandtabs(20))

        for acl_type, acl_value in acls.items():
            print("{} \t {}".format(acl_type, acl_value).expandtabs(20))
        else:
            print('<no acls>')

        print()

    print("\n" * 10)
    sys.exit(0)

# add
new_acl_type = sys.argv[2]
new_acl_value = sys.argv[3]

room_id = str(uuid())
env.db.add_default_room(room_id)

channel_id = env.db.channel_for_room(room_id)
acl_manager.update_room_acl(channel_id, room_id, ApiActions.AUTOJOIN, new_acl_type, new_acl_value)

print("added room {} with acls {}={}".format(room_id, new_acl_type, new_acl_value))

print("\n"*10)