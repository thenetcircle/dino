from zope.interface import Interface
from typing import Union, Dict


class ICache(Interface):
    def get_user_for_sid(self, sid: str):
        """
        get the user id for a sig

        :param sid: the s session id
        :return: the user id or none
        """

    def get_all_permanent_rooms(self):
        """

        :return:
        """

    def set_all_permanent_rooms(self, rooms):
        """

        :param rooms:
        :return:
        """

    def get_room_acls_for_action(self, action: str) -> Union[None, Dict[str, Dict[str, str]]]:
        """

        :param action:
        :return:
        """

    def set_room_acls_for_action(self, action: str, acls: Dict[str, Dict[str, str]]) -> None:
        """

        :param action:
        :param acls:
        :return:
        """

    def add_heartbeat(self, user_id: str) -> None:
        """
        add a new heartbeat when a user has authenticated through the rest api

        :param user_id: the uuid of the user
        :return: nothing
        """

    def check_heartbeat(self, user_id: str) -> None:
        """
        check if a user's heartbeat has expired or not, and if it hasn't, update the ttl

        :param user_id: the uuid of the user
        :return: true if still online, false otherwise
        """

    def has_heartbeat(self, user_id: str) -> bool:
        """
        check if user has been authenticated to get a heartbeat

        :param user_id: the uuid of the user
        :return: true if existing, false otherwise
        """

    def set_is_room_ephemeral(self, room_id: str, is_ephemeral: bool) -> None:
        """
        set whether aroom is ephemeral (temporary) or not

        :param room_id: the uuid of the room
        :param is_ephemeral: boolean for whether or not it is ephemeral
        :return: nothing
        """

    def set_type_of_rooms_in_channel(self, channel_id: str, object_type: str) -> None:
        """
        type of rooms in a channel, if all rooms are static or all rooms are temporary, otherwise mix

        :param channel_id: uuid of the channel
        :param object_type: the type of rooms: static, temporary or mix
        :return: nothing
        """

    def get_type_of_rooms_in_channel(self, channel_id: str) -> str:
        """
        type of rooms in a channel, if all rooms are static or all rooms are temporary, otherwise mix

        :param channel_id: the uuid of the channel
        :return: static, temporary or mix
        """

    def get_rooms_for_user(self, user_id: str) -> dict:
        """
        get all rooms for this user in form of a dict {room_uuid: room_name}

        :param user_id: the uuid of the user
        :return: a dict {room_uuid: room_name}
        """

    def set_rooms_for_user(self, user_id: str, rooms: dict) -> None:
        """
        set the room uuids the user is in; ttl of 20-30 seconds (random)

        :param user_id: the uuid of the user
        :param rooms: a dict of rooms the user is in now {room_uuid: room_name}
        :return: nothing
        """

    def leave_room_for_user(self, user_id: str, room_id: str) -> None:
        """
        remove this user form the dict of rooms this user is in
        :param user_id:
        :param room_id:
        :return:
        """

    def is_user_in_room(self, user_id: str, room_id: str) -> bool:
        """
        check if this user is this room according to the cache

        :param user_id: the uuid of the user
        :param room_id: the room uuid
        :return: True/False
        """

    def remove_rooms_for_user(self, user_id: str) -> None:
        """
        remove all rooms the cache thinks this user is in

        :param user_id: the uuid of the user
        :return: nothing
        """

    def set_user_in_room(self, user_id: str, room_id: str, room_name: str) -> None:
        """
        mark this user to be in this room

        :param user_id: the uuid of the user
        :param room_id: the room uuid
        :param room_name: the name of the room
        :return: nothing
        """

    def clear_default_rooms(self) -> None:
        """
        clear the list of default room uuids from the cache

        :return: nothing
        """
    def set_default_rooms(self, rooms: list) -> None:
        """
        set the list of default rooms in the cache

        :param rooms: a list of room uuids
        :return: nothing
        """

    def reset_rooms_for_channel(self, channel_id: str) -> None:
        """
        delete the cached rooms for the channel

        :param channel_id: uuid of the channel
        :return: nothing
        """

    def reset_sids_for_user(self, user_id: str) -> None:
        """
        reset all cached sids for this user, if any

        :param user_id: the id of the user
        :return: nothing
        """

    def add_sid_for_user(self, user_id: str, sid: str) -> None:
        """
        add one sid to be cached for this user

        :param user_id: the id of the user
        :param sid: the sid to cache
        :return: nothing
        """

    def set_sids_for_user(self, user_id: str, all_sids: list) -> None:
        """
        cache a list of sids for this user, will overwrite if any previous sid has been cached

        :param user_id: the id of the user
        :param all_sids: a list of sids to cache
        :return: nothing
        """

    def remove_sid_for_user(self, user_id: str, sid: str) -> None:
        """
        remove a specific cached sid for a user, if it exists

        :param user_id: the id of the user
        :param sid: the sid to remove
        :return: nothing
        """

    def get_sids_for_user(self, user_id: str) -> Union[None, list]:
        """
        get all sids for this user, or None if not cached

        :param user_id: id of the user
        :return: a list of sids or None if not cached
        """

    def get_rooms_for_channel(self, channel_id: str, with_info: bool = True) -> dict:
        """
        get the rooms for this channel with or without info

        returned info is a dict of dicts (or None of not found):

            rooms[room.uuid] = {
                'name': room.name,
                'sort_order': room.sort_order,
                'ephemeral': room.ephemeral,
                'users': len(visible_users)
            }

        if with_info=False:

            rooms[room.uuid] = {
                'name': room.name,
                'ephemeral': room.ephemeral
            }

        :param channel_id: uuid of the channel
        :param with_info: boolean, if true (default), will include n_users and is_ephemeral in output
        :return: the room infos
        """

    def set_rooms_for_channel(self, channel_id: str, rooms_infos: dict, with_info: bool = True) -> None:
        """
        set the room info for this channel

        room_infos should be a dict of dicts like this:

            rooms[room.uuid] = {
                'name': room.name,
                'sort_order': room.sort_order,
                'ephemeral': room.ephemeral,
                'users': len(visible_users)
            }

        :param channel_id: uuid of the channel
        :param rooms_infos: the room infos
        :param with_info: if the rooms_infos includes ephemeral and users tag or not
        :return: nothing
        """

    def reset_channels_with_sort(self):
        """
        remove the cache channels

        :return: nothing
        """

    def get_channels_with_sort(self):
        """
        get all channels with their sort value, in this format:

            {channel_uuid: (channel_name, sort_value)}

        :return: the channels
        """

    def set_channels_with_sort(self, channels):
        """
        cache all channels with their sort value, in this format:

            {channel_uuid: (channel_name, sort_value)}

        :param channels: the channels
        :return: nothing
        """

    def get_acls_in_room_for_action(self, room_id: str, action: str) -> dict:
        """
        get the acls for this room and action (join, message, etc.)

        :param room_id: the uuid of the room
        :param action: the action
        :return: dict
        """

    def set_acls_in_room_for_action(self, room_id: str, action: str, acls: dict) -> None:
        """
        set acls in this room for an action

        :param room_id: the uuid of the room
        :param action: the action
        :param acls: dict of acls
        :return: nothing
        """

    def get_acls_in_channel_for_action(self, channel_id: str, action: str) -> dict:
        """
        get the acls for this channel and action (join, message, etc.)

        :param channel_id: the uuid of the channel
        :param action: the action
        :return: dict
        """

    def get_users_in_room_for_role(self, room_id: str, role: str) -> dict:
        """
        get the users who have this role for this room

        :param room_id: the uuid of the room
        :param role: the role key
        :return: dict of user_id -> user_name
        """

    def set_users_in_room_for_role(self, room_id: str, role: str, users: dict) -> None:
        """
        set the users who have this role for this room

        :param room_id: the uuid of the room
        :param role: the role key
        :param users: a dict of user_id -> user_name
        :return: nothing
        """

    def reset_users_in_room_for_role(self, room_id: str, role: str) -> None:
        """
        reset the users who have this role for this room

        :param room_id: the uuid of the room
        :param role: the role key
        :return: nothing
        """

    def get_users_in_channel_for_role(self, channel_id: str, role: str) -> dict:
        """
        get the users who have this role for this channel

        :param channel_id: the uuid of the channel
        :param role: the role key
        :return: dict of user_id -> user_name
        """

    def set_users_in_channel_for_role(self, channel_id: str, role: str, users: dict) -> None:
        """
        set the users who have this role for this channel

        :param channel_id: the uuid of the channel
        :param role: the role key
        :param users: a dict of user_id -> user_name
        :return: nothing
        """

    def reset_users_in_channel_for_role(self, channel_id: str, role: str) -> None:
        """
        reset the users who have this role for this channel

        :param channel_id: the uuid of the channel
        :param role: the role key
        :return: nothing
        """

    def set_acls_in_channel_for_action(self, channel_id: str, action: str, acls: dict) -> None:
        """
        set acls in this channel for an action

        :param channe_id: the uuid of the channel
        :param action: the action
        :param acls: dict of acls
        :return: nothing
        """

    def reset_acls_in_channel_for_action(self, channel_id: str, action: str) -> None:
        """
        delete the cached acls for this room for an action

        :param room_id: the uuid of the room
        :param action: the action to remove for
        :return: nothing
        """

    def reset_acls_in_room_for_action(self, room_id: str, action: str) -> None:
        """
        delete the cached acls for this room

        :param room_id: the uuid of the room
        :param action: the action to remove for
        :return: nothing
        """

    def reset_acls_in_channel(self, channel_id: str) -> None:
        """
        delete the cached acls for this channel

        :param channel_id: the uuid of the channel
        :return: nothing
        """

    def reset_acls_in_room(self, room_id: str) -> None:
        """
        delete the cached acls for this room

        :param room_id: the uuid of the room
        :return: nothing
        """

    def get_users_in_room(self, room_id: str, is_super_user: bool) -> dict:
        """
        short-lived cache of users in a room, depending on if super super or not (non-super users can't see invisible
        users), in this format:

            {user_id: user_name}

        :param room_id: the uuid of the room
        :param is_super_user: boolean; if either a super user or global moderator then True, otherwise False
        :return: a dict of users in the room
        """

    def set_users_in_room(self, room_id: str, users: dict, is_super_user: bool) -> None:
        """
        short-lived cache of users in a room, depending on if super super or not (non-super users can't see invisible
        users), in this format:

            {user_id: user_name}

        :param room_id: the uuid of the room
        :param is_super_user: boolean; if either a super user or global moderator then True, otherwise False
        :return: nothing
        """

    def set_all_acls_for_channel(self, channel_id: str, acls: dict) -> None:
        """
        set acls in this channel

        :param channel_id: the uuid of the channel
        :param action: the action
        :param acls: dict of acls
        :return: nothing
        """

    def set_all_acls_for_room(self, room_id: str, acls: dict) -> None:
        """
        set acls in this room

        :param room_id: the uuid of the room
        :param acls: dict of acls
        :return: nothing
        """

    def get_all_acls_for_channel(self, channel_id: str) -> dict:
        """
        get all acls for this channel

        :param channel_id: the uuid of the channel
        :return: a dict of acls
        """

    def get_all_acls_for_room(self, room_id: str) -> dict:
        """
        get all acls for this room

        :param room_id: the uuid of the room
        :return: a dict of acls
        """

    def get_default_rooms(self) -> list:
        """
        get a list of default room uuids (auto-join)

        :return: a list of room uuids
        """

    def is_room_ephemeral(self, room_id: str) -> bool:
        """
        check if a room is ephemeral (temporary) or not

        :param room_id: the uuid of the room
        :return: true if ephemeral, false if not, or None of not in cache or TTL expired
        """

    def get_admin_room(self) -> str:
        """
        get the room uuid of the admin room, or None if no such room exists

        :return: the uuid of the admin room, or None of not found
        """

    def remove_admin_room(self) -> None:
        """
        remove the cached admin room

        :return: nothing
        """

    def remove_from_black_list(self, word: str) -> None:
        """
        remove a word from the black list

        :param word: a word to remove if it exists
        :return: nothing
        """

    def reset_black_list(self) -> None:
        """
        clear the cached black list

        :return: nothing
        """

    def add_to_black_list(self, word: str) -> None:
        """
        add a word to the black list

        :param word: a word to add
        :return: nothing
        """

    def get_black_list(self) -> set:
        """
        return the cached black list; a set of forbidden words

        :return: a set of forbidden words, or None of not in the cache
        """

    def set_black_list(self, the_list: set) -> None:
        """
        set the black list in the cache

        :param the_list: a set of forbidden words
        :return: nothing
        """

    def reset_user_roles(self, user_id: str) -> None:
        """
        invalidate roles in cache; used when roles change in db
        :param user_id: the id of the user to invalidate the cache for
        :return: nothing
        """

    def get_user_roles(self, user_id: str) -> dict:
        """
        get all the user roles for a user

        :param user_id: the id of the user
        :return: a dict of global, channel and room roles
        """

    def set_user_roles(self, user_id: str, roles: dict) -> None:
        """
        set all the roles for a user

        :param user_id: the id of the user
        :param roles: all the roles for this user
        :return: nothing
        """

    def set_global_ban_timestamp(self, user_id: str, duration: str, timestamp: str, username: str) -> None:
        """
        set the global ban timestamp for a user to a given timestamp

        :param user_id: the id of the user
        :param duration: the duration, e.g. 12d
        :param timestamp: the timestamp
        :param username: the username of this user
        :return: nothing
        """

    def set_channel_ban_timestamp(self, channel_id: str, user_id: str, duration: str, timestamp: str, username: str) -> None:
        """
        set the ban timestamp on channel for a user to a given timestamp

        :param user_id: the id of the user
        :param channel_id: the uuid of the channel
        :param duration: the duration, e.g. 12d
        :param timestamp: the timestamp
        :param username: the username of this user
        :return: nothing
        """

    def set_room_ban_timestamp(self, room_id: str, user_id: str, duration: str, timestamp: str, username: str) -> None:
        """
        set the ban timestamp on a room for a user to a given timestamp

        :param user_id: the id of the user
        :param room_id: the uuid of the room
        :param duration: the duration, e.g. 12d
        :param timestamp: the timestamp
        :param username: the username of this user
        :return: nothing
        """

    def get_global_ban_timestamp(self, user_id: str) -> str:
        """
        get the ban timestamp of the user in the given room, or empty string if no ban exist

        :param user_id: the id of the user
        :return: the timestamp in ConfigKeys.DEFAULT_DATE_FORMAT format, or '' if no ban exists
        """

    def get_channel_ban_timestamp(self, channel_id: str, user_id: str) -> str:
        """
        get the ban timestamp of the user in the given channel, or empty string if no ban exist

        :param channel_id: the uuid of the channel
        :param user_id: the id of the user
        :return: the timestamp in ConfigKeys.DEFAULT_DATE_FORMAT format, or '' if no ban exists
        """

    def get_room_ban_timestamp(self, room_id: str, user_id: str) -> str:
        """
        get the ban timestamp of the user in the given room, or empty string if no ban exist

        :param room_id: the uuid of the room
        :param user_id: the id of the user
        :return: the timestamp in ConfigKeys.DEFAULT_DATE_FORMAT format, or '' if no ban exists
        """

    def remove_room_id_for_name(self, channel_id: str, room_name: str) -> None:
        """
        remove the cache id for the room name

        :param channel_id: uuid of the channel
        :param room_name: name of the room
        :return: nothing
        """

    def get_room_id_for_name(self, channel_id: str, room_name: str) -> str:
        """

        :param channel_id:
        :param room_name:
        :return:
        """

    def set_room_id_for_name(self, channel_id, room_name, room_id):
        """

        :param channel_id:
        :param room_name:
        :param room_id:
        :return:
        """

    def get_user_name(self, user_id: str) -> str:
        """
        the the name of the user from the id

        :param user_id: the id of the user
        :return: the name of the user
        """

    def set_user_name(self, user_id: str, user_name: str) -> None:
        """
        set the name of a user in the cache

        :param user_id: the id of the user
        :param user_name: the name of the user
        :return: nothing
        """

    def remove_channel_exists(self, channel_id: str) -> None:
        """
        remove the existence of a room in the cache

        :param channel_id: the uuid of the channel
        :return: nothing
        """

    def remove_room_exists(self, channel_id, room_id):
        """
        when removing a room we wan't to be able to remove it from the cache as well

        :param channel_id: the uuid of the channel
        :param room_id: the uuid of the room
        :return: nothing
        """

    def set_admin_room(self, room_id: str) -> None:
        """

        :param room_id:
        :return:
        """

    def set_user_status(self, user_id: str, status: str) -> None:
        """

        :param user_id:
        :param status:
        :return:
        """

    def set_channel_name(self, channel_id: str, channel_name: str) -> None:
        """

        :param channel_id:
        :param channel_name:
        :return:
        """

    def get_room_exists(self, channel_id, room_id):
        """

        :param channel_id:
        :param room_id:
        :return:
        """

    def get_channel_name(self, channel_id: str) -> str:
        """

        :param channel_id:
        :return:
        """

    def get_room_name(self, room_id: str) -> str:
        """

        :param room_id:
        :return:
        """

    def set_room_name(self, room_id: str, room_name: str) -> str:
        """

        :param room_id:
        :param room_name:
        :return:
        """

    def get_user_info(self, user_id: str) -> dict:
        """
        get the cached user info

        :param user_id: the id of the user
        :return: a dict of user info key key -> user info value
        """

    def set_user_info(self, user_id: str, info: dict) -> None:
        """
        cache the user info

        :param user_id: the id fo the user
        :param info: a dict of user info key key -> user info value
        :return: nothing
        """

    def reset_user_info(self, user_id: str) -> None:
        """
        delete the cache user info

        :param user_id: id of the user
        :return: nothing
        """

    def set_room_exists(self, channel_id, room_id, room_name):
        """

        :param channel_id:
        :param room_id:
        :param room_name:
        :return:
        """

    def set_channel_exists(self, channel_id: str) -> None:
        """

        :param channel_id:
        :return:
        """

    def set_channel_for_room(self, channel_id: str, room_id: str) -> None:
        """

        :param channel_id:
        :param room_id:
        :return:
        """

    def get_channel_exists(self, channel_id):
        """

        :param channel_id:
        :return:
        """

    def get_channel_for_room(self, room_id):
        """

        :param room_id:
        :return:
        """

    def get_user_status(self, user_id: str):
        """

        :param user_id:
        :return:
        """

    def user_check_status(self, user_id, other_status):
        """

        :param user_id:
        :param other_status:
        :return:
        """

    def user_is_offline(self, user_id):
        """

        :param user_id:
        :return:
        """

    def user_is_online(self, user_id):
        """

        :param user_id:
        :return:
        """

    def user_is_invisible(self, user_id):
        """

        :param user_id:
        :return:
        """

    def user_is_in_multicast(self, user_id):
        """

        :param user_id:
        :return:
        """

    def remove_from_multicast_on_disconnect(self, user_id: str) -> None:
        """

        :param user_id:
        :return:
        """

    def set_user_offline(self, user_id: str) -> None:
        """

        :param user_id:
        :return:
        """

    def set_user_online(self, user_id: str) -> None:
        """

        :param user_id:
        :return:
        """

    def set_user_status_invisible(self, user_id: str) -> None:
        """
        only sets the user status to invisible, used for when chaning visibility status while a user is offline

        :param user_id:
        :return:
        """

    def set_user_invisible(self, user_id: str) -> None:
        """

        :param user_id:
        :return:
        """
