# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from st2common.models.db import MongoDBAccess
from st2common.models.db.policy import PolicyTypeDB, PolicyDB
from st2common.persistence.base import Access


class PolicyType(Access):
    impl = MongoDBAccess(PolicyTypeDB)

    @classmethod
    def _get_impl(cls):
        return cls.impl

    @classmethod
    def _get_by_object(cls, object):
        # PolicyType name is unique.
        name = getattr(object, 'name', '')
        return cls.get_by_name(name)


class Policy(Access):
    impl = MongoDBAccess(PolicyDB)

    @classmethod
    def _get_impl(cls):
        return cls.impl
