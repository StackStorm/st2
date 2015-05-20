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

from st2common.exceptions import db as db_exc
from st2common.models import db
from st2common.models.db import stormbase


__all__ = [
    'LockDB'
]


class LockDB(stormbase.StormBaseDB):
    name = me.StringField(required=True, unique=True)
    value = me.IntField(required=True, default=1)
    owner = me.StringField()
    proc_info = me.DictField(required=True)
    expiry = me.DateTimeField(required=True)

    meta = {
        'indexes': [
            {
                'fields': ['expiry'],
                'expireAfterSeconds': 0
            }
        ]
    }


class LockAccess(db.MongoDBAccess):

    def get(self, exclude_fields=None, *args, **kwargs):
        exclude_fields = ['owner'] if not exclude_fields else exclude_fields + ['owner']
        return super(LockAccess, self).get(exclude_fields=exclude_fields, *args, **kwargs)

    def query(self, offset=0, limit=None, order_by=None, exclude_fields=None, **filters):
        exclude_fields = ['owner'] if not exclude_fields else exclude_fields + ['owner']
        return super(LockAccess, self).query(offset=offset,
                                             limit=limit,
                                             order_by=order_by,
                                             exclude_fields=exclude_fields,
                                             **filters)

    @classmethod
    def distinct(cls, *args, **kwargs):
        raise NotImplementedError()

    @classmethod
    def aggregate(cls, *args, **kwargs):
        raise NotImplementedError()

    def delete(self, instance):
        self.model.objects(id=instance.id, owner=getattr(instance, 'owner', '')).delete()

        try:
            if self.get_by_name(instance.name):
                raise db_exc.StackStormDBObjectFoundError('Lock still exists.')
        except ValueError:
            pass


MODELS = [LockDB]
