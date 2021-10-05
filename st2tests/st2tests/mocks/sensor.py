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

"""
Mock classes for use in pack testing.
"""

from __future__ import absolute_import

from logging import RootLogger

from mock import Mock

from st2common.models.api.trace import TraceContext
from st2reactor.container.sensor_wrapper import SensorService
from st2tests.mocks.datastore import MockDatastoreService

__all__ = ["MockSensorWrapper", "MockSensorService"]


class MockSensorWrapper(object):
    def __init__(self, pack, class_name):
        self._pack = pack
        self._class_name = class_name


class MockSensorService(SensorService):
    """
    Mock SensorService for use in testing.
    """

    def __init__(self, sensor_wrapper):
        self._sensor_wrapper = sensor_wrapper

        # Holds a mock logger instance
        # We use a Mock class so use can assert logger was called with particular arguments
        self._logger = Mock(spec=RootLogger)

        # Holds a list of triggers which were dispatched
        self.dispatched_triggers = []

        self._datastore_service = MockDatastoreService(
            logger=self._logger,
            pack_name=self._sensor_wrapper._pack,
            class_name=self._sensor_wrapper._class_name,
        )

    @property
    def datastore_service(self):
        return self._datastore_service

    def get_logger(self, name):
        """
        Return mock logger instance.

        Keep in mind that this method returns Mock class instance which means you can use all the
        usual Mock class methods to assert that a particular message has been logged / logger has
        been called with particular arguments.
        """
        return self._logger

    def dispatch(self, trigger, payload=None, trace_tag=None):
        trace_context = TraceContext(trace_tag=trace_tag) if trace_tag else None
        return self.dispatch_with_context(
            trigger=trigger, payload=payload, trace_context=trace_context
        )

    def dispatch_with_context(self, trigger, payload=None, trace_context=None):
        item = {"trigger": trigger, "payload": payload, "trace_context": trace_context}
        self.dispatched_triggers.append(item)
        return item
