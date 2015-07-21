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

from oslo_config import cfg

from st2common import transport
from st2common.models.db.sensor import sensor_type_access, sensor_instance_access, \
    sensor_execution_access
from st2common.persistence.base import Access, ContentPackResource


class SensorType(ContentPackResource):
    impl = sensor_type_access
    publisher = None

    @classmethod
    def _get_impl(cls):
        return cls.impl

    @classmethod
    def _get_publisher(cls):
        if not cls.publisher:
            cls.publisher = transport.reactor.SensorCUDPublisher(cfg.CONF.messaging.url)
        return cls.publisher


class SensorInstance(ContentPackResource):
    impl = sensor_instance_access
    publisher = None

    @classmethod
    def _get_impl(cls):
        return cls.impl

    @classmethod
    def _get_publisher(cls):
        if not cls.publisher:
            cls.publisher = transport.reactor.SensorInstanceCUDPublisher(cfg.CONF.messaging.url)
        return cls.publisher


class SensorExecution(Access):
    impl = sensor_execution_access

    @classmethod
    def _get_impl(cls):
        return cls.impl
