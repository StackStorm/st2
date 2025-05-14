# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# All Exchanges and Queues related to liveaction.

from __future__ import absolute_import

from st2common.transport import publishers
from st2common.transport.kombu import Exchange, Queue

__all__ = ["LiveActionPublisher", "get_queue", "get_status_management_queue"]


LIVEACTION_XCHG = Exchange("st2.liveaction", type="topic")
LIVEACTION_STATUS_MGMT_XCHG = Exchange("st2.liveaction.status", type="topic")


class LiveActionPublisher(publishers.CUDPublisher, publishers.StatePublisherMixin):
    def __init__(self):
        publishers.CUDPublisher.__init__(self, exchange=LIVEACTION_XCHG)
        publishers.StatePublisherMixin.__init__(
            self, exchange=LIVEACTION_STATUS_MGMT_XCHG
        )


def get_queue(name, routing_key):
    return Queue(name, LIVEACTION_XCHG, routing_key=routing_key)


def get_status_management_queue(name, routing_key):
    return Queue(name, LIVEACTION_STATUS_MGMT_XCHG, routing_key=routing_key)
