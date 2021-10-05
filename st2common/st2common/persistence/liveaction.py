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

from __future__ import absolute_import

from st2common import transport
from st2common.models.db.liveaction import liveaction_access
from st2common.persistence import base as persistence

__all__ = ["LiveAction"]


class LiveAction(persistence.StatusBasedResource):
    impl = liveaction_access
    publisher = None

    @classmethod
    def _get_impl(cls):
        return cls.impl

    @classmethod
    def _get_publisher(cls):
        if not cls.publisher:
            cls.publisher = transport.liveaction.LiveActionPublisher()
        return cls.publisher

    @classmethod
    def delete_by_query(cls, *args, **query):
        return cls._get_impl().delete_by_query(*args, **query)
