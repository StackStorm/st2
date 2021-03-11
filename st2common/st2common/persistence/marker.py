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
from st2common.models.db import MongoDBAccess
from st2common.models.db.marker import MarkerDB
from st2common.models.db.marker import DumperMarkerDB
from st2common.persistence.base import Access

__all__ = ["Marker"]


class Marker(Access):
    impl = MongoDBAccess(MarkerDB)
    publisher = None

    @classmethod
    def _get_impl(cls):
        return cls.impl


class DumperMarker(Access):
    impl = MongoDBAccess(DumperMarkerDB)
    publisher = None

    @classmethod
    def _get_impl(cls):
        return cls.impl
