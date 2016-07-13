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

import re
import unittest2

from st2common.hooks import AUTH_TOKENS_URL_REGEX


class ApiHookTest(unittest2.TestCase):

    def test_auth_exception_regex(self):
        self.assertEqual(re.search(AUTH_TOKENS_URL_REGEX, '/tokens').group(), '/tokens')
        self.assertEqual(re.search(AUTH_TOKENS_URL_REGEX, '/v1/tokens').group(), '/v1/tokens')
        self.assertEqual(re.search(AUTH_TOKENS_URL_REGEX, '/v30/tokens').group(), '/v30/tokens')
        self.assertIsNone(re.search(AUTH_TOKENS_URL_REGEX, '/abc/tokens'))
        self.assertIsNone(re.search(AUTH_TOKENS_URL_REGEX, '/vabc/tokens'))
        self.assertIsNone(re.search(AUTH_TOKENS_URL_REGEX, '/tokens/abc'))
        self.assertIsNone(re.search(AUTH_TOKENS_URL_REGEX, '/abc/tokens/def'))
        self.assertIsNone(re.search(AUTH_TOKENS_URL_REGEX, '/actions'))
