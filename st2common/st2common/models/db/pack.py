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

import mongoengine as me

from st2common.models.db import MongoDBAccess
from st2common.models.db import stormbase

__all__ = [
    'PackDB'
]


class PackDB(stormbase.StormFoundationDB):
    """
    System entity which represents a pack.
    """
    ref = me.StringField(required=True, unique=True)
    name = me.StringField(required=True, unique=True)
    description = me.StringField(required=True)
    keywords = me.ListField(field=me.StringField())
    version = me.StringField(required=True)  # TODO: Enforce format
    author = me.StringField(required=True)
    email = me.EmailField(required=True)
    files = me.ListField(field=me.StringField())

# specialized access objects
pack_access = MongoDBAccess(PackDB)

MODELS = [PackDB]
