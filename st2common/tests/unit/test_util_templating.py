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
from st2tests.base import CleanDbTestCase
from st2common.constants.keyvalue import FULL_USER_SCOPE
from st2common.models.db.keyvalue import KeyValuePairDB
from st2common.persistence.keyvalue import KeyValuePair
from st2common.util.templating import render_template_with_system_and_user_context


class TemplatingUtilsTestCase(CleanDbTestCase):
    def setUp(self):
        super(TemplatingUtilsTestCase, self).setUp()

        # Insert mock DB objects
        kvp_1_db = KeyValuePairDB(name="key1", value="valuea")
        kvp_1_db = KeyValuePair.add_or_update(kvp_1_db)

        kvp_2_db = KeyValuePairDB(name="key2", value="valueb")
        kvp_2_db = KeyValuePair.add_or_update(kvp_2_db)

        kvp_3_db = KeyValuePairDB(
            name="stanley:key1", value="valuestanley1", scope=FULL_USER_SCOPE
        )
        kvp_3_db = KeyValuePair.add_or_update(kvp_3_db)

        kvp_4_db = KeyValuePairDB(
            name="joe:key1", value="valuejoe1", scope=FULL_USER_SCOPE
        )
        kvp_4_db = KeyValuePair.add_or_update(kvp_4_db)

    def test_render_template_with_system_and_user_context(self):
        # 1. No reference to the user inside the template
        template = "{{st2kv.system.key1}}"
        user = "stanley"

        result = render_template_with_system_and_user_context(value=template, user=user)
        self.assertEqual(result, "valuea")

        template = "{{st2kv.system.key2}}"
        user = "stanley"

        result = render_template_with_system_and_user_context(value=template, user=user)
        self.assertEqual(result, "valueb")

        # 2. Reference to the user inside the template
        template = "{{st2kv.user.key1}}"
        user = "stanley"

        result = render_template_with_system_and_user_context(value=template, user=user)
        self.assertEqual(result, "valuestanley1")

        template = "{{st2kv.user.key1}}"
        user = "joe"

        result = render_template_with_system_and_user_context(value=template, user=user)
        self.assertEqual(result, "valuejoe1")
