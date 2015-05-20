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

from st2common import log as logging
from st2common.models.db import synchronization as sync_models
from st2common.persistence import base as persistence


LOG = logging.getLogger(__name__)


class Lock(persistence.Access):
    impl = sync_models.LockAccess(sync_models.LockDB)

    @classmethod
    def _get_impl(cls):
        return cls.impl

    @classmethod
    def _get_by_object(cls, instance):
        return cls.get_by_name(getattr(instance, 'name', ''))

    @classmethod
    def add_or_update(cls, model_object, publish=True):
        raise NotImplementedError('Use the "add" method. Update is not supported for locks.')
