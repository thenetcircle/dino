# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import sys
import traceback

from activitystreams.models.activity import Activity

from dino import environ
from dino import utils
from dino.config import ConfigKeys
from dino.endpoint.queue import QueueHandler
from dino.environ import GNEnvironment
from dino.wio.environ import WioEnvironment

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'

logger = logging.getLogger(__name__)


def overrides(interface_class):
    def overrider(method):
        assert(method.__name__ in dir(interface_class))
        return method
    return overrider


class WioQueueHandler(QueueHandler):
    def __init__(self, socketio, env: WioEnvironment):
        super().__init__(socketio, GNEnvironment(skip_init=True))
        self.env = env

    @overrides(QueueHandler)
    def user_is_on_this_node(self, activity: Activity) -> bool:
        if self.env.node not in {'app', 'wio'}:
            return False

        namespace = activity.target.url or '/ws'
        user_id = activity.object.id
        user_sids = utils.get_sids_for_user_id(user_id)

        try:
            logger.debug('checking if we have user %s in namespace %s' % (user_id, namespace))
            for user_sid in user_sids:
                if user_sid in self.socketio.server.manager.rooms[namespace]:
                    logger.debug('found user %s on this node' % user_id)
                    return True
            logger.info('no user %s for namespace [%s] (or user not on this node)' % (user_id, namespace))
            return False
        except KeyError as e:
            logger.warning('namespace %s does not exist (maybe this is web/rest node?): %s' % (namespace, str(e)))
            return False
        except Exception as e:
            logger.error('could not get user sids for namespace "%s" and user_id "%s": %s' % (namespace, user_id, str(e)))
            logger.exception(traceback.format_exc())
            return False

    @overrides(QueueHandler)
    def create_ban_even_if_not_on_this_node(self, activity: Activity) -> None:
        """
        since bans can be created through the rest api we need to create the ban even though the user might not be on
        this node, since one reason could be that he's not even connected. So make sure the ban is created first.
        """
        banned_id = activity.object.id
        target_type = 'global'

        reason = None
        if hasattr(activity.object, 'content'):
            reason = activity.object.content

        try:
            ban_duration = activity.object.summary
            ban_timestamp = utils.ban_duration_to_timestamp(ban_duration)
            activity.object.updated = utils.ban_duration_to_datetime(ban_duration)\
                .strftime(ConfigKeys.DEFAULT_DATE_FORMAT)
            banner_id = activity.actor.id

            self.send_ban_event_to_external_queue(activity, target_type)

            logger.info('banning user %s globally for %s' % (banned_id, ban_duration))
            self.env.db.ban_user_global(banned_id, ban_timestamp, ban_duration, reason, banner_id)
        except KeyError as ke:
            logger.error('could not ban: %s' % str(ke))
            logger.exception(traceback.format_exc())

    @overrides(QueueHandler)
    def handle_local_node_events(self, data: dict, activity: Activity):
        # do this first, since ban might occur even if user is not connected
        if activity.verb != 'ban':
            return

        user_is_on_node = True

        # delegate so we don't end up re-reading this event before adding to ignore list
        if not self.user_is_on_this_node(activity):
            logger.info('user is not on this node, will publish on queue for other nodes to try')
            self.update_recently_delegated_events(activity.id)
            environ.env.publish(data)
            user_is_on_node = False

        self.create_ban_even_if_not_on_this_node(activity)

        # no need to continue if the user is not on this node; event already delegated
        if not user_is_on_node:
            return

        try:
            self.handle_ban(activity)
        except Exception as e:
            logger.error('could not handle ban: %s' % str(e))
            logger.exception(traceback.format_exc())

    @overrides(QueueHandler)
    def _handle_server_activity(self, data: dict, activity: Activity) -> None:
        if activity.id in self.recently_delegated_events_set:
            logger.info('ignoring event with id %s since we delegated from this node' % activity.id)
            return
        if activity.id in self.recently_handled_events_set:
            logger.info('ignoring event with id %s since we already handled it on this node' % activity.id)
            return

        logger.debug('got internally published event with verb %s id %s' % (activity.verb, activity.id))
        self.update_recently_handled_events(activity.id)

        if activity.verb in ['ban', 'remove']:
            self.handle_local_node_events(data, activity)
        else:
            # otherwise it's external events for possible analysis
            environ.env.publish(data, external=True)

    @overrides(QueueHandler)
    def kick(self, orig_data: dict, activity: Activity, room_id: str, user_id: str, user_sids: list, namespace: str) -> None:
        # can't kick in wio, only ban
        raise NotImplementedError()

    @overrides(QueueHandler)
    def handle_ban(self, activity: Activity):
        banned_id = activity.object.id
        if not utils.is_valid_id(banned_id):
            logger.warning('got invalid id on ban activity: {}'.format(str(activity.id)))
            return

        banned_name = utils.get_user_name_for(banned_id)
        banned_sids = utils.get_sids_for_user_id(banned_id)
        namespace = activity.target.url or '/ws'

        if banned_sids is None or len(banned_sids) == 0 or banned_sids == [None] or banned_sids[0] == '':
            logger.warning('no sid(s) found for user id %s' % banned_id)
            return

        try:
            self.env.db.set_user_offline(banned_id)
            disconnect_activity = utils.activity_for_disconnect(banned_id, banned_name)
            self.env.publish(disconnect_activity, external=True)

            ban_activity = self.get_ban_activity(activity, '')
            self.env.out_of_scope_emit(
                    'gn_banned', ban_activity, json=True, namespace=namespace, room=banned_id)

        except KeyError as ke:
            logger.error('could not ban: %s' % str(ke))
            logger.exception(traceback.format_exc())
            self.env.capture_exception(sys.exc_info())

    @overrides(QueueHandler)
    def send_kick_event_to_external_queue(self, activity: Activity) -> None:
        raise NotImplementedError()
