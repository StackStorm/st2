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

from st2tests.api import APIControllerWithRBACTestCase

__all__ = [
    'UserControllerTestCase'
]


class UserControllerTestCase(APIControllerWithRBACTestCase):
    def test_get(self):
        self.use_user(self.users['observer'])
        resp = self.app.get('/v1/user')
        self.assertEqual(resp.json['username'], 'observer')
        self.assertEqual(resp.json['rbac']['enabled'], True)
        self.assertEqual(resp.json['rbac']['is_admin'], False)
        self.assertEqual(resp.json['rbac']['roles'], ['observer'])
        self.assertEqual(resp.json['authentication']['method'], 'authentication token')
        self.assertEqual(resp.json['authentication']['location'], 'header')
        self.use_user(self.users['admin'])

        resp = self.app.get('/v1/user')
        self.assertEqual(resp.json['username'], 'admin')
        self.assertEqual(resp.json['rbac']['enabled'], True)
        self.assertEqual(resp.json['rbac']['is_admin'], True)
        self.assertEqual(resp.json['rbac']['roles'], ['admin'])
        self.assertEqual(resp.json['authentication']['method'], 'authentication token')
        self.assertEqual(resp.json['authentication']['location'], 'header')
