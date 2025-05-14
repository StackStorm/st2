# Copyright 2022 The StackStorm Authors.
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

__all__ = [
    "ActionAliasPublisher",
    "get_queue",
]

ACTIONALIAS_XCHG = Exchange("st2.actionalias", type="topic")


class ActionAliasPublisher(publishers.CUDPublisher):
    def __init__(self):
        super(ActionAliasPublisher, self).__init__(exchange=ACTIONALIAS_XCHG)


def get_queue(name=None, routing_key=None, exclusive=False, auto_delete=False):
    return Queue(
        name,
        ACTIONALIAS_XCHG,
        routing_key=routing_key,
        exclusive=exclusive,
        auto_delete=auto_delete,
    )
