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

from st2common import log as logging
from st2common.metrics.base import BaseMetricsDriver

__all__ = ["EchoDriver"]

LOG = logging.getLogger(__name__)


class EchoDriver(BaseMetricsDriver):
    """
    Driver which logs / LOG.debugs out each metrics operation which would have been performed.
    """

    def time(self, key, time):
        LOG.debug("[metrics] time(key=%s, time=%s)" % (key, time))

    def inc_counter(self, key, amount=1):
        LOG.debug("[metrics] counter.incr(%s, %s)" % (key, amount))

    def dec_counter(self, key, amount=1):
        LOG.debug("[metrics] counter.decr(%s, %s)" % (key, amount))

    def set_gauge(self, key, value):
        LOG.debug("[metrics] set_gauge(%s, %s)" % (key, value))

    def inc_gauge(self, key, amount=1):
        LOG.debug("[metrics] gauge.incr(%s, %s)" % (key, amount))

    def dec_gauge(self, key, amount=1):
        LOG.debug("[metrics] gauge.decr(%s, %s)" % (key, amount))
