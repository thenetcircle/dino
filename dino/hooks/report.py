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
from dino import utils

__author__ = 'Oscar Eriksson <oscar.eriks@gmail.com>'


class OnReportHooks(object):
    @staticmethod
    def publish_activity(arg: tuple) -> None:
        _, activity = arg
        report_activity = utils.activity_for_report(activity)
        environ.env.publish(report_activity, external=True)

    @staticmethod
    def notify_admins(arg: tuple) -> None:
        _, activity = arg
        report_activity = utils.activity_for_report(activity)
        admin_room_id = utils.get_admin_room()
        environ.env.emit('gn_reported', report_activity, json=True, broadcast=True, room=admin_room_id, namespace='/ws')


@environ.env.observer.on('on_report')
def _on_report_publish_activity(arg: tuple) -> None:
    OnReportHooks.publish_activity(arg)


@environ.env.observer.on('on_report')
def _on_report_notify_admins(arg: tuple) -> None:
    OnReportHooks.notify_admins(arg)
