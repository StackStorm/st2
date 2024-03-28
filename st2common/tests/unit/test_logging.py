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
import unittest

from st2common.logging.misc import get_logger_name_for_module
from st2reactor.cmd import sensormanager
from python_runner import python_runner
from st2common import runners

__all__ = ["LoggingMiscUtilsTestCase"]


class LoggingMiscUtilsTestCase(unittest.TestCase):
    def test_get_logger_name_for_module(self):
        logger_name = get_logger_name_for_module(sensormanager)
        self.assertEqual(logger_name, "st2reactor.cmd.sensormanager")

        logger_name = get_logger_name_for_module(python_runner)
        result = logger_name.endswith(
            "contrib.runners.python_runner.python_runner.python_runner"
        )
        self.assertTrue(result)

        logger_name = get_logger_name_for_module(
            python_runner, exclude_module_name=True
        )
        self.assertTrue(
            logger_name.endswith("contrib.runners.python_runner.python_runner")
        )

        logger_name = get_logger_name_for_module(runners)
        self.assertEqual(logger_name, "st2common.runners.__init__")

        logger_name = get_logger_name_for_module(runners, exclude_module_name=True)
        self.assertEqual(logger_name, "st2common.runners")
