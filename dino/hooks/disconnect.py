import logging
import sys
import traceback

from activitystreams.models.target import Target

from dino import environ
from dino import utils
from dino.config import SessionKeys
from dino.config import UserKeys
from dino.exceptions import NoSuchUserException

logger = logging.getLogger(__name__)


class OnDisconnectHooks(object):
    @staticmethod
    def handle_disconnect(arg: tuple, is_socket_disconnect: bool=False) -> None:
        """
        when a client disconnects this hook will handle the related logic

        :param arg: tuple of (data, parsed_activity)
        :param is_socket_disconnect: true if normal websocket connection, false if long-lives heartbeat session
        :return: nothing
        """

        def set_user_offline(user_id, current_sid, user_status):
            all_sids = utils.get_sids_for_user_id(user_id)

            # update last_online on every session closure
            if user_status != UserKeys.STATUS_INVISIBLE:
                try:
                    environ.env.db._set_last_online(user_id)
                    environ.env.cache._set_last_online(user_id)
                except Exception as e:
                    logger.error('could not set last_online in db for user {}: {}'.format(user_id, str(e)))
                    logger.exception(traceback.format_exc())
                    environ.env.capture_exception(sys.exc_info())

            # only one of the user sessions disconnected
            if len(all_sids) > 1:
                return

            try:
                if not utils.is_valid_id(user_id):
                    logger.warning('got invalid id on disconnect for act: {}'.format(str(activity.id)))
                    # TODO: sentry
                    return

                environ.env.db.remove_sid_for_user(user_id, current_sid)
                all_sids = utils.get_sids_for_user_id(user_id)

                # if the user still has another session up we don't set the user as offline
                if len(all_sids) > 0:
                    logger.debug('when setting user offline, found other sids: [%s]' % ','.join(all_sids))
                    return

                if user_status == UserKeys.STATUS_INVISIBLE:
                    environ.env.cache.remove_from_multicast_on_disconnect(user_id)
                else:
                    environ.env.db.set_user_offline(user_id)
            except Exception as e:
                logger.error('could not set user offline: %s' % str(e))
                logger.debug('request for failed set_user_offline(): %s' % str(data))
                logger.exception(traceback.format_exc())
                environ.env.capture_exception(sys.exc_info())

        def leave_private_room(user_id, current_sid):
            all_sids = utils.get_sids_for_user_id(user_id)

            # only one of the user sessions disconnected
            if len(all_sids) > 1:
                return

            try:
                # todo: only broadcast 'offline' status if currently 'online' (i.e. don't broadcast if e.g. 'invisible')
                user_name = environ.env.session.get(SessionKeys.user_name.value)
                logger.debug('a user disconnected [id: "%s", name: "%s", sid: "%s"]' % (user_id, user_name, current_sid))

                try:
                    environ.env.leave_room(current_sid)
                    environ.env.db.remove_sid_for_user(user_id, current_sid)
                except Exception as e:
                    logger.warning('could not remove sid {} for user {}: {}'.format(current_sid, user_id, str(e)))

                if user_id is None or len(user_id.strip()) == 0:
                    return

                all_sids = utils.get_sids_for_user_id(user_id)
                all_sids = all_sids.copy()

                if len(all_sids) == 0 or (current_sid in all_sids and len(all_sids) == 1):
                    environ.env.leave_room(user_id)
                    environ.env.db.reset_sids_for_user(user_id)
                    for key in SessionKeys.temporary_keys.value:
                        environ.env.auth.update_session_for_key(activity.actor.id, key, False)

            except Exception as e:
                logger.error('could not leave private room: %s' % str(e))
                logger.debug('request for failed leave_private_room(): %s' % str(data))
                logger.exception(traceback.format_exc())
                environ.env.capture_exception(sys.exc_info())

        def leave_all_public_rooms_and_emit_leave_events(user_id, current_sid):
            # we don't involve db join/leave for public rooms in wio, and don't emit events for it either
            # TODO: commented this, since we still need it for live-streaming in wio nodes; double check it
            #  doesn't cause other issues
            # if environ.env.node == 'wio':
            #     return

            try:
                user_name = environ.env.session.get(SessionKeys.user_name.value)
                rooms = environ.env.db.rooms_for_user(user_id, skip_cache=True)

                for room_id, room_name in rooms.items():
                    """
                    environ.env.db.remove_sid_for_user_in_room(user_id, room_id, current_sid)

                    if utils.is_multiple_sessions_allowed():
                        sids_in_room = environ.env.db.sids_for_user_in_room(user_id, room_id)

                        # race condition could cause fetching to happen before deletion... just
                        # make sure that current_sid it's not in this set
                        try:
                            sids_in_room.remove(current_sid)
                        except KeyError:
                            pass

                        # still have other sessions in this room
                        if len(sids_in_room) > 0:
                            logger.info('user {} ({}) still have other sids in room: {}'.format(
                                user_id, user_name, ','.join(sids_in_room)
                            ))
                            continue
                    """

                    if 'target' not in data:
                        data['target'] = dict()
                    data['target']['id'] = room_id

                    if not hasattr(activity, 'target'):
                        activity.target = Target({'id': room_id})
                    else:
                        activity.target.id = room_id

                    utils.remove_user_from_room(user_id, user_name, room_id)
                    environ.env.emit(
                        'gn_user_left',
                        utils.activity_for_leave(user_id, user_name, room_id, room_name),
                        room=room_id,
                        namespace='/ws'
                    )
                    utils.check_if_remove_room_empty(activity, is_delayed_removal=True)

                environ.env.db.remove_current_rooms_for_user(user_id)
            except Exception as e:
                logger.error('could not leave all public rooms: %s' % str(e))
                logger.debug('request for failed leave_all_public_rooms_and_emit_leave_events(): %s' % str(data))
                logger.exception(traceback.format_exc())
                environ.env.capture_exception(sys.exc_info())

        def emit_disconnect_event(user_id, current_sid, user_status) -> None:
            try:
                if is_socket_disconnect:
                    user_name = environ.env.session.get(SessionKeys.user_name.value)
                    if user_name is None or len(user_name.strip()) == 0:
                        try:
                            user_name = utils.get_user_name_for(user_id)
                        except NoSuchUserException:
                            user_name = '<unknown>'
                else:
                    try:
                        user_name = utils.get_user_name_for(user_id)
                    except NoSuchUserException:
                        user_name = '<unknown>'

                all_sids = utils.get_sids_for_user_id(user_id)

                # race condition might lead to db cache saying it's still there or similar
                make_sure_current_sid_removed(all_sids, user_id, current_sid)

                if user_id is None or user_id == 'None':
                    logger.warning('blank user_id on disconnect event, trying sid instead')

                    if current_sid is None or current_sid == 'None' or current_sid == '':
                        logger.error('blank sid as well as blank user id, ignoring disconnect event')
                        return

                    try:
                        user_id = utils.get_user_for_sid(current_sid)
                    except Exception as e:
                        logger.warning('could not get user id from sid "{}": {}'.format(current_sid, str(e)))
                        environ.env.capture_exception(sys.exc_info())
                        user_id = '-1'

                    if user_id is None or len(user_id.strip()) == 0:
                        logger.warning('blank user id for sid "{}"'.format(current_sid))
                        user_id = '-1'

                logger.debug(
                    'sid %s disconnected, all_sids: [%s] for user %s (%s)' % (
                        current_sid, ','.join(all_sids), user_id, user_name))

                if user_id != '-1':
                    sid_ended_event = utils.activity_for_sid_disconnect(user_id, user_name, current_sid)
                    environ.env.publish(sid_ended_event, external=True)

                # if the user still has another session up we don't send disconnect event
                if all_sids is not None and len(all_sids) > 0:
                    return

                if user_id != '-1':
                    activity_json = utils.activity_for_disconnect(user_id, user_name)

                    # update last_online on every session closure
                    if user_status == UserKeys.STATUS_INVISIBLE:
                        # invisible shouldn't get their last online at updated, so use the previous known time
                        utils.add_last_online_at_to_event(activity_json, use_now=False)
                    else:
                        utils.add_last_online_at_to_event(activity_json, use_now=True)

                    environ.env.publish(activity_json, external=True)

            except Exception as e:
                logger.error('could not emit disconnect event: %s' % str(e))
                logger.debug('request for failed emit_disconnect_event(): %s' % str(data))
                logger.exception(traceback.format_exc())
                environ.env.capture_exception(sys.exc_info())

        def make_sure_current_sid_removed(all_sids, user_id, current_sid):
            if current_sid in all_sids:
                try:
                    all_sids.remove(current_sid)
                    environ.env.db.remove_sid_for_user(user_id, current_sid)
                except Exception as e:
                    logger.warning('could not remove current sid: {}'.format(str(e)))
                    logger.exception(traceback.format_exc())
                    environ.env.capture_exception(sys.exc_info())

        data, activity = arg
        _user_id = activity.actor.id

        # TODO: check why we NEED skip_cache=True here, when false, the value we get is not the value we have in
        #  redis; could be the in-memory cache that's containing the incorrect value... check more
        _user_status = utils.get_user_status(_user_id, skip_cache=True)

        if is_socket_disconnect:
            _current_sid = environ.env.request.sid
            leave_private_room(_user_id, _current_sid)
            leave_all_public_rooms_and_emit_leave_events(_user_id, _current_sid)
        else:
            _current_sid = 'hb-{}'.format(_user_id)

        emit_disconnect_event(_user_id, _current_sid, _user_status)
        set_user_offline(_user_id, _current_sid, _user_status)


@environ.env.observer.on('on_disconnect')
def _on_disconnect_handle_disconnect(arg: tuple) -> None:
    OnDisconnectHooks.handle_disconnect(arg, is_socket_disconnect=True)


@environ.env.observer.on('on_heartbeat_disconnect')
def _on_disconnect_handle_disconnect_heartbeat(arg: tuple) -> None:
    OnDisconnectHooks.handle_disconnect(arg, is_socket_disconnect=False)
