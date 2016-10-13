# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the 'License'); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from unittest2 import TestCase

from st2common.jinja.filters import time


class TestTimeJinjaFilters(TestCase):

    def test_to_human_time_from_seconds(self):
        self.assertEqual('0s', time.to_human_time_from_seconds(seconds=0))
        self.assertEqual('0.1\u03BCs', time.to_human_time_from_seconds(seconds=0.1))
        self.assertEqual('56s', time.to_human_time_from_seconds(seconds=56))
        self.assertEqual('56s', time.to_human_time_from_seconds(seconds=56.2))
        self.assertEqual('7m36s', time.to_human_time_from_seconds(seconds=456))
        self.assertEqual('1h16m0s', time.to_human_time_from_seconds(seconds=4560))
        self.assertEqual('1y12d16h36m37s', time.to_human_time_from_seconds(seconds=45678997))
        self.assertRaises(AssertionError, time.to_human_time_from_seconds,
                          seconds='stuff')
