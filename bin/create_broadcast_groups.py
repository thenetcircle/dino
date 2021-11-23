from uuid import uuid4 as uuid
import sys

from dino.environ import env
from dino.config import ApiActions
from dino.db.manager import AclManager, RoomManager

print("\n"*10)

if len(sys.argv) < 2 or sys.argv[1] not in {"list", "add"}:
    print("usage: DINO_ENVIRONMENT=<env> ./create_broadcast_groups.py list")
    print("usage: DINO_ENVIRONMENT=<env> ./create_broadcast_groups.py add country=de,it,gb membership=normal,vip user_type=1,2,3")
    print("\n"*10)
    sys.exit(1)


acl_manager = AclManager(env)
room_manager = RoomManager(env)

room_acls = env.db.get_room_acls_for_action(ApiActions.AUTOJOIN)

if sys.argv[1] == "list":
    for room_id, acls in room_acls.items():
        if room_id is None or len(room_id.strip()) == 0:
            continue

        print("{}: {}".format(room_id, env.db.get_room_name(room_id)))
        print("type \t value".expandtabs(20))
        print("---- \t -----".expandtabs(20))
        if len(acls):
            for acl_type, acl_value in acls.items():
                print("{} \t {}".format(acl_type, acl_value).expandtabs(20))
        else:
            print('<no acls>')
        print()

    print("\n" * 10)

# add
else:
    channel_id = env.db.channel_for_room(room_acls.keys()[0])
    args = list()

    for arg in sys.argv[2:]:
        k, v = arg.split("=")
        v = v.split(",")
        args.append((k, v))

    for i in range(len(args[2][1])):
        for j in range(len(args[1][1])):
            for k in range(len(args[0][1])):
                room_id = str(uuid())

                # country=de,it,gb membership=normal,vip user_type=1,2,3
                room_name = "{}-{}-{}".format(args[0][1][k], args[1][1][j], args[2][1][i])
                room_manager.create_room(room_name, room_id, channel_id, "0")

                acl_manager.update_room_acl(channel_id, room_id, ApiActions.AUTOJOIN, args[0][0], args[0][1][k])
                acl_manager.update_room_acl(channel_id, room_id, ApiActions.AUTOJOIN, args[1][0], args[1][1][j])
                acl_manager.update_room_acl(channel_id, room_id, ApiActions.AUTOJOIN, args[2][0], args[2][1][i])

                print("added room {} with acls:".format(room_id))
                print("{}={}".format(args[0][0], args[0][1][k]))
                print("{}={}".format(args[1][0], args[1][1][j]))
                print("{}={}".format(args[2][0], args[2][1][i]))
                print()

    print("\n" * 10)
