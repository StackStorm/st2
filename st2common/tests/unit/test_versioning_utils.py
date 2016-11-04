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

from st2common.util.versioning import complex_semver_match


class VersioningUtilsTestCase(unittest2.TestCase):
    def test_complex_semver_match(self):
        # Positive test case
        self.assertTrue(complex_semver_match('1.6.0', '>=1.6.0, <2.2.0'))
        self.assertTrue(complex_semver_match('1.6.1', '>=1.6.0, <2.2.0'))
        self.assertTrue(complex_semver_match('2.0.0', '>=1.6.0, <2.2.0'))
        self.assertTrue(complex_semver_match('2.1.0', '>=1.6.0, <2.2.0'))
        self.assertTrue(complex_semver_match('2.1.9', '>=1.6.0, <2.2.0'))

        self.assertTrue(complex_semver_match('1.6.0', '>=1.6.0'))
        self.assertTrue(complex_semver_match('1.6.1', '>=1.6.0'))
        self.assertTrue(complex_semver_match('2.1.0', '>=1.6.0'))

        # Negative test case
        self.assertFalse(complex_semver_match('1.5.0', '>=1.6.0, <2.2.0'))
        self.assertFalse(complex_semver_match('0.1.0', '>=1.6.0, <2.2.0'))
        self.assertFalse(complex_semver_match('2.2.1', '>=1.6.0, <2.2.0'))
        self.assertFalse(complex_semver_match('2.3.0', '>=1.6.0, <2.2.0'))
        self.assertFalse(complex_semver_match('3.0.0', '>=1.6.0, <2.2.0'))

        self.assertFalse(complex_semver_match('1.5.0', '>=1.6.0'))
        self.assertFalse(complex_semver_match('0.1.0', '>=1.6.0'))
        self.assertFalse(complex_semver_match('1.5.9', '>=1.6.0'))
