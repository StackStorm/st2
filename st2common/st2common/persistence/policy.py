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
from st2common.models.db.policy import PolicyTypeReference, PolicyTypeDB, PolicyDB
from st2common.persistence.base import Access, ContentPackResource


class PolicyType(Access):
    impl = MongoDBAccess(PolicyTypeDB)

    @classmethod
    def _get_impl(cls):
        return cls.impl

    @classmethod
    def get_by_ref(cls, ref):
        if ref:
            ref_obj = PolicyTypeReference.from_string_reference(ref=ref)
            result = cls.query(name=ref_obj.name, resource_type=ref_obj.resource_type).first()
            return result
        else:
            return None

    @classmethod
    def _get_by_object(cls, object):
        name = getattr(object, 'name', '')
        resource_type = getattr(object, 'resource_type', '')
        ref = PolicyTypeReference.to_string_reference(resource_type=resource_type, name=name)
        return cls.get_by_ref(ref)


class Policy(ContentPackResource):
    impl = MongoDBAccess(PolicyDB)

    @classmethod
    def _get_impl(cls):
        return cls.impl
