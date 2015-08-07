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

import eventlet
import unittest2

from st2reactor.container.process_container import ProcessSensorContainer

import st2tests.config as tests_config
tests_config.parse_args()


class ProcessContainerTests(unittest2.TestCase):

    def test_no_sensors_dont_quit(self):
        process_container = ProcessSensorContainer(None, poll_interval=0.1)
        process_container_thread = eventlet.spawn(process_container.run)
        eventlet.sleep(0.5)
        self.assertEqual(process_container.running(), 0)
        self.assertEqual(process_container.stopped(), False)
        process_container.shutdown()
        process_container_thread.kill()
