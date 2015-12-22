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

import unittest2

from st2common.logging.misc import get_logger_name_for_module
from st2reactor.cmd import sensormanager
from st2actions.runners import pythonrunner
from st2actions import runners

__all__ = [
    'LoggingMiscUtilsTestCase'
]


class LoggingMiscUtilsTestCase(unittest2.TestCase):
    def test_get_logger_name_for_module(self):
        logger_name = get_logger_name_for_module(sensormanager)
        self.assertEqual(logger_name, 'st2reactor.cmd.sensormanager')

        logger_name = get_logger_name_for_module(pythonrunner)
        self.assertEqual(logger_name, 'st2actions.runners.pythonrunner')

        logger_name = get_logger_name_for_module(runners)
        self.assertEqual(logger_name, 'st2actions.runners.__init__')
