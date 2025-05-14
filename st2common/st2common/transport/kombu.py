# Copyright 2024 The StackStorm Authors.
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

from __future__ import absolute_import

import kombu
from oslo_config import cfg


class Exchange(kombu.Exchange):
    def __call__(self, *args, **kwargs):
        # update exchange name with prefix just before binding (as late as possible).
        prefix = cfg.CONF.messaging.prefix
        if self.name and prefix != "st2":
            self.name = self.name.replace("st2.", f"{prefix}.", 1)
        return super().__call__(*args, **kwargs)


class Queue(kombu.Queue):
    def __call__(self, *args, **kwargs):
        # update queue name with prefix just before binding (as late as possible).
        prefix = cfg.CONF.messaging.prefix
        if self.name and prefix != "st2":
            self.name = self.name.replace("st2.", f"{prefix}.", 1)
        return super().__call__(*args, **kwargs)
