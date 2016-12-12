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

from dino import environ

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class OnSetAclHooks(object):
    @staticmethod
    def set_acl(arg: tuple) -> None:
        data, activity = arg

        target_id = activity.target.id
        is_for_channel = activity.target.object_type == 'channel'

        acl_dict = dict()
        for acl in activity.object.attachments:
            # if the content is None, it means we're removing this ACL
            if acl.content is None:
                if is_for_channel:
                    environ.env.db.delete_acl_in_channel_for_action(target_id, acl.object_type, acl.summary)
                else:
                    environ.env.db.delete_acl_in_room_for_action(target_id, acl.object_type, acl.summary)
                continue

            if acl.summary not in acl_dict:
                acl_dict[acl.summary] = dict()
            acl_dict[acl.summary][acl.object_type] = acl.content

        # might have only removed acls, so could be size 0
        if len(acl_dict) > 0:
            for api_action, acls in acl_dict.items():
                if is_for_channel:
                    environ.env.db.add_acls_in_channel_for_action(target_id, api_action, acls)
                else:
                    environ.env.db.add_acls_in_room_for_action(target_id, api_action, acls)


@environ.env.observer.on('on_set_acl')
def _on_set_acl_set_acl(arg: tuple) -> None:
    OnSetAclHooks.set_acl(arg)
